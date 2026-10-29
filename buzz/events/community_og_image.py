"""The share image of a team's public page: the Buzz band, the team mark, its name and stats."""

import io
from dataclasses import dataclass

import frappe
from frappe import _
from PIL import Image, ImageDraw

from buzz.events.banner_pattern import rings_banner
from buzz.events.og_image import (
	COLOURS,
	PADDING,
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
# A one-line short description under the name, off until the design calls for it
SHOW_DESCRIPTION = False

WIDTH, HEIGHT = 1200, 630
RIGHT = WIDTH - PADDING
CONTENT_WIDTH = RIGHT - PADDING

NAME_SIZE, NAME_LINES = 54, 2
DESCRIPTION_SIZE, DESCRIPTION_INK = 26, "#6b6b6b"
NUMBER_SIZE, LABEL_SIZE, LABEL_GAP = 30, 26, 8
STATS_MIDDLE, STATS_GAP = 551, 44
BRAND_TOP, HOST_SIZE, HOST_HEIGHT, HOST_GAP = PADDING, 20, 24, 10


@dataclass(frozen=True)
class Layout:
	"""Vertical rhythm. The stats stay put; the band and the type above them adapt."""

	band_height: int = 264
	name_first_middle: int = 406
	line_height: int = 64
	description_middle: int | None = None  # None: no description line

	def avatar_top(self) -> int:
		return self.band_height - MARK_SIZE // 2


# A description line is paid for by a shorter band, so the stats row stays where it is
DESCRIBED_ONE_LINE = Layout(band_height=224, name_first_middle=384, line_height=62, description_middle=458)
DESCRIBED_TWO_LINES = Layout(band_height=224, name_first_middle=353, line_height=62, description_middle=488)


def generate(team_name: str):
	team = frappe.get_doc("Buzz Team", team_name)
	if not team.is_published:
		clear(team)
		return
	render_if_stale(CommunityOgImage(team))


def enqueue_generate(team_name: str):
	frappe.enqueue(
		"buzz.events.community_og_image.generate",
		team_name=team_name,
		job_id=f"og-image-team-{team_name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def enqueue_all_published():
	"""Daily: upcoming counts drift as events pass, and the input hash skips unchanged teams."""
	for name in frappe.get_all("Buzz Team", filters={"is_published": 1}, pluck="name"):
		enqueue_generate(str(name))


@dataclass
class Stat:
	number: int
	label: str


class CommunityOgImage(OgImage):
	"""A team's share image. Its counts are read from the same place as its page's."""

	render_version = RENDER_VERSION

	def __init__(self, team):
		self.team, self.doc = team, team
		self.colours = dict(COLOURS["light"])
		with site_language():
			self.name = team.team_name
			self.description = (team.short_description or "") if SHOW_DESCRIPTION else ""
			self.stats = self.build_stats()

	def build_stats(self) -> list[Stat]:
		from buzz.events.doctype.buzz_team.team_page import team_event_counts

		counts = team_event_counts(self.team)
		stats = []
		if counts.upcoming:
			stats.append(Stat(counts.upcoming, _("Upcoming")))
		if counts.hosted:
			stats.append(Stat(counts.hosted, _("Event Hosted") if counts.hosted == 1 else _("Events Hosted")))
		return stats

	def hash_parts(self) -> list:
		stats = [(stat.number, stat.label) for stat in self.stats]
		return [self.name, self.description, stats, self.team.logo]

	def can_render(self) -> bool:
		return is_drawable(self.name + self.description)

	def layout(self) -> Layout:
		if not self.description:
			return Layout()
		return DESCRIBED_TWO_LINES if len(self.name_lines()) > 1 else DESCRIBED_ONE_LINE

	def render(self) -> bytes:
		layout = self.layout()
		image = Image.new("RGB", (WIDTH, HEIGHT), self.colours["page-bg"])
		image.paste(self.band(layout), (0, 0))
		ImageDraw.Draw(image).line(
			[(0, layout.band_height), (WIDTH, layout.band_height)], fill=self.colours["border"], width=1
		)
		TeamMark(self.team, self.colours, layout.avatar_top()).draw(image, PADDING)
		self.draw_brand(image)
		self.draw_name(image, layout)
		self.draw_description(image, layout)
		self.draw_stats(image)
		output = io.BytesIO()
		image.save(output, "PNG", optimize=True)
		return output.getvalue()

	def band(self, layout: Layout) -> Image.Image:
		size = (WIDTH, layout.band_height)
		return rings_banner(self.name, size, self.colours["border"], self.colours["surface"])

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

	def draw_name(self, image: Image.Image, layout: Layout):
		for index, line in enumerate(self.name_lines()):
			OgText(line, font("SemiBold", NAME_SIZE), tracking(NAME_SIZE)).draw(
				image,
				(PADDING, layout.name_first_middle + index * layout.line_height),
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

	def draw_description(self, image: Image.Image, layout: Layout):
		if not self.description or layout.description_middle is None:
			return
		OgText(self.description, font("Medium", DESCRIPTION_SIZE)).fit(CONTENT_WIDTH).draw(
			image, (PADDING, layout.description_middle), DESCRIPTION_INK
		)

	def draw_stats(self, image: Image.Image):
		if not self.stats:
			return
		left = PADDING
		for stat in self.stats:
			draw_stat(image, stat, left, self.colours)
			left += stat_width(stat) + STATS_GAP


def draw_stat(image: Image.Image, stat: Stat, left: float, colours: dict):
	"""Number then label on a shared baseline, anchored so the ink centres on STATS_MIDDLE."""
	number_font, label_font = font("SemiBold", NUMBER_SIZE), font("Medium", LABEL_SIZE)
	baseline = STATS_MIDDLE + round(0.36 * NUMBER_SIZE)
	number = str(stat.number)
	draw = ImageDraw.Draw(image)
	draw.text((left, baseline), number, font=number_font, fill=colours["ink-title"], anchor="ls")
	draw.text(
		(left + number_font.getlength(number) + LABEL_GAP, baseline),
		stat.label,
		font=label_font,
		fill=colours["ink-muted"],
		anchor="ls",
	)


def stat_width(stat: Stat) -> float:
	number_font, label_font = font("SemiBold", NUMBER_SIZE), font("Medium", LABEL_SIZE)
	return number_font.getlength(str(stat.number)) + LABEL_GAP + label_font.getlength(stat.label)


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
