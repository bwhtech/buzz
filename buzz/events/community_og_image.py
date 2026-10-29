"""The share image of a team's public page: the Buzz band, the team mark, its name and stats."""

import io

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
	recoloured_wordmark,
	render_if_stale,
	site_host,
	site_language,
)
from buzz.events.og_text import OgText, font, is_drawable, tracking
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
	"""A published team draws a fresh image, a private one clears a leftover."""
	# A live worker would render test teams mid-test and race their teardown
	if frappe.in_test or not team_name:
		return
	if any(frappe.db.get_value("Buzz Team", team_name, ["is_published", "og_image"]) or ()):
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
		output = io.BytesIO()
		image.save(output, "PNG", optimize=True)
		return output.getvalue()

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
		"""Two lines at most: a longer name folds into line two, then ends in an ellipsis."""
		lines = wrap_name(self.name) or [""]
		if len(lines) > NAME_LINES:
			joined = " ".join(lines[NAME_LINES - 1 :])
			lines = [*lines[: NAME_LINES - 1], joined]
		lines[-1] = (
			OgText(lines[-1], font("SemiBold", NAME_SIZE), tracking(NAME_SIZE)).fit(CONTENT_WIDTH).text
		)
		return lines

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


def wrap_name(text: str) -> list[str]:
	"""Greedy word wrap, so a two-line name breaks where it reads best."""
	typeface, spacing = font("SemiBold", NAME_SIZE), tracking(NAME_SIZE)
	lines, words = [], text.split()
	while words:
		line, words = take_line(words, typeface, spacing)
		lines.append(line)
	return lines


def take_line(words: list[str], typeface, spacing: float) -> tuple[str, list[str]]:
	line = words[0]
	for index in range(1, len(words)):
		candidate = f"{line} {words[index]}"
		if OgText(candidate, typeface, spacing).width() > CONTENT_WIDTH:
			return line, words[index:]
		line = candidate
	return line, []
