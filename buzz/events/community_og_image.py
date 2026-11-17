"""The share image of a team's public page: the Buzz band, the team mark, its name and stats."""

import frappe
from frappe import _
from PIL import Image, ImageDraw

from buzz.events.banner_pattern import rings_banner
from buzz.events.doctype.buzz_team.team_page import TeamPage
from buzz.events.og_image import (
	COLOURS,
	HEIGHT,
	PADDING,
	WIDTH,
	WORDMARK_SIZE,
	OgImage,
	clear,
	png_bytes,
	recoloured_wordmark,
	render_if_stale,
	site_host,
	site_language,
)
from buzz.events.og_text import OgText, font, is_drawable, tracking, wrap_lines
from buzz.events.team_mark import MARK_SIZE, TeamMark

RENDER_VERSION = 1

RIGHT = WIDTH - PADDING
CONTENT_WIDTH = RIGHT - PADDING

BAND_HEIGHT = 264
AVATAR_TOP = BAND_HEIGHT - MARK_SIZE // 2
NAME_SIZE, NAME_LINES, NAME_FIRST_MIDDLE, NAME_LINE_HEIGHT = 54, 2, 406, 64
NUMBER_SIZE, LABEL_SIZE, LABEL_GAP = 30, 26, 8
STATS_MIDDLE, STATS_GAP = 551, 44
BRAND_TOP, HOST_SIZE, HOST_HEIGHT, HOST_GAP = PADDING, 20, 24, 10


def generate(team_name: str):
	# The team may be deleted before the job runs
	if not frappe.db.exists("Buzz Team", team_name):
		return
	team = frappe.get_doc("Buzz Team", team_name)
	if not team.is_published:
		clear(team)
		return
	image = CommunityOgImage(team)
	# A logo that fails to load keeps the current image, so the next run retries
	if not image.mark.logo_failed_to_load():
		render_if_stale(image)


def enqueue_generate(team_name: str):
	frappe.enqueue(
		"buzz.events.community_og_image.generate",
		team_name=team_name,
		job_id=f"og-image-team-{team_name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def enqueue_generate_for(team_name: str | None):
	"""A published team draws a fresh image, a private one clears a leftover.

	A personal team is never published: its image is its owner's profile image.
	"""
	from buzz.events import profile_og_image

	# A live worker would render test teams mid-test and race their teardown
	if frappe.in_test or not team_name:
		return
	row = frappe.db.get_value(
		"Buzz Team", team_name, ["is_personal", "is_published", "og_image"], as_dict=True
	)
	if row and row.is_personal:
		profile_og_image.enqueue_generate(team_name)
	elif row and (row.is_published or row.og_image):
		enqueue_generate(team_name)


def enqueue_all_published():
	"""Daily: upcoming counts drift as events pass, and the input hash skips unchanged teams."""
	for name in frappe.get_all("Buzz Team", filters={"is_published": 1}, pluck="name"):
		enqueue_generate(str(name))


class CommunityOgImage(OgImage):
	"""A team's share image. Its counts are read from the same place as its page's."""

	render_version = RENDER_VERSION

	def __init__(self, team):
		self.team, self.doc = team, team
		self.colours = dict(COLOURS["light"])
		self.mark = TeamMark(team, self.colours, AVATAR_TOP)
		with site_language():
			self.name = team.team_name
			self.stats = self.build_stats()

	def build_stats(self) -> list[tuple[int, str]]:
		page = TeamPage(self.team)
		stats = []
		if page.upcoming_count:
			stats.append((page.upcoming_count, _("Upcoming")))
		if page.hosted_count:
			stats.append(
				(page.hosted_count, _("Event Hosted") if page.hosted_count == 1 else _("Events Hosted"))
			)
		return stats

	def hash_parts(self) -> list:
		return [self.name, self.stats, self.team.logo]

	def can_render(self) -> bool:
		return is_drawable(self.name)

	def render(self) -> bytes:
		image = Image.new("RGB", (WIDTH, HEIGHT), self.colours["page-bg"])
		image.paste(self.band(), (0, 0))
		ImageDraw.Draw(image).line(
			[(0, BAND_HEIGHT), (WIDTH, BAND_HEIGHT)], fill=self.colours["border"], width=1
		)
		self.mark.draw(image, PADDING)
		self.draw_brand(image)
		self.draw_name(image)
		self.draw_stats(image)
		return png_bytes(image)

	def band(self) -> Image.Image:
		return rings_banner(self.name, (WIDTH, BAND_HEIGHT), self.colours["border"], self.colours["surface"])

	def draw_brand(self, image: Image.Image):
		wordmark = recoloured_wordmark(self.colours["ink-title"])
		image.paste(wordmark, (RIGHT - WORDMARK_SIZE[0], BRAND_TOP), wordmark)
		host = site_host()
		if not host:
			return
		ImageDraw.Draw(image).text(
			(RIGHT, BRAND_TOP + WORDMARK_SIZE[1] + HOST_GAP + HOST_HEIGHT // 2),
			host,
			font=font("Medium", HOST_SIZE),
			fill=self.colours["ink-muted"],
			anchor="rm",
		)

	def draw_name(self, image: Image.Image):
		for index, line in enumerate(self.name_lines()):
			OgText(line, font("SemiBold", NAME_SIZE), tracking(NAME_SIZE)).draw(
				image,
				(PADDING, NAME_FIRST_MIDDLE + index * NAME_LINE_HEIGHT),
				self.colours["ink-title"],
			)

	def name_lines(self) -> list[str]:
		return wrap_lines(self.name, font("SemiBold", NAME_SIZE), CONTENT_WIDTH, NAME_LINES)

	def draw_stats(self, image: Image.Image):
		"""Number then label on a shared baseline, so the ink centres on STATS_MIDDLE."""
		draw = ImageDraw.Draw(image)
		number_font, label_font = font("SemiBold", NUMBER_SIZE), font("Medium", LABEL_SIZE)
		baseline = STATS_MIDDLE + round(0.36 * NUMBER_SIZE)
		left = PADDING
		for number, label in self.stats:
			text = str(number)
			label_left = left + number_font.getlength(text) + LABEL_GAP
			draw.text((left, baseline), text, font=number_font, fill=self.colours["ink-title"], anchor="ls")
			draw.text(
				(label_left, baseline), label, font=label_font, fill=self.colours["ink-muted"], anchor="ls"
			)
			left = label_left + label_font.getlength(label) + STATS_GAP
