import re
from functools import cache

import frappe
from PIL import Image, ImageDraw, ImageFont

FONTS = frappe.get_app_path("buzz", "public", "fonts")
# The emoji font holds colour bitmaps at this size only; runs are drawn at it and scaled down
EMOJI_FONT_SIZE = 109
# Inter covers Latin, Greek and Cyrillic; other scripts would draw as empty boxes.
# A code-point range is coarser than reading the font's cmap, which needs fontTools.
INTER = "\u0000-\u052f\u1e00-\u20cf"
EMOJI = f"(?:[0-9#*]\ufe0f?\u20e3|[^{INTER}])"
EMOJI_RUN = re.compile(f"({EMOJI}(?:\u200d?{EMOJI})*)")


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
	return ImageFont.truetype(f"{FONTS}/Inter-{weight}.woff2", size)


@cache
def emoji_font() -> ImageFont.FreeTypeFont:
	return ImageFont.truetype(f"{FONTS}/NotoColorEmoji.ttf", EMOJI_FONT_SIZE)


@cache
def in_emoji_font(character: str) -> bool:
	# Joiners and selectors have no width; a missing glyph has width but no pixels
	typeface = emoji_font()
	return not typeface.getlength(character) or bool(typeface.getmask(character).getbbox())


def is_drawable(text: str) -> bool:
	return all(re.match(f"[{INTER}]", character) or in_emoji_font(character) for character in text)


def tracking(size: int) -> float:
	return -0.03 * size


class OgText:
	"""A line of Inter text with colour emoji, which Pillow cannot draw from a single font."""

	def __init__(self, text: str, typeface: ImageFont.FreeTypeFont, letter_spacing: float = 0):
		self.text = text
		self.typeface = typeface
		self.letter_spacing = letter_spacing
		self.emoji_scale = typeface.size / EMOJI_FONT_SIZE

	def runs(self) -> list[tuple[bool, str]]:
		# re.split with a capture group alternates plain text and emoji runs
		return [(index % 2 == 1, run) for index, run in enumerate(EMOJI_RUN.split(self.text))]

	def run_width(self, is_emoji: bool, run: str) -> float:
		if is_emoji:
			return emoji_font().getlength(run) * self.emoji_scale
		return self.typeface.getlength(run) + self.letter_spacing * len(run)

	def width(self) -> float:
		return sum(self.run_width(is_emoji, run) for is_emoji, run in self.runs())

	def fit(self, max_width: float) -> "OgText":
		if self.width() <= max_width:
			return self
		text = self.text
		while text and self.with_text(text + "…").width() > max_width:
			text = text[:-1]
		return self.with_text(text.rstrip() + "…")

	def with_text(self, text: str) -> "OgText":
		return OgText(text, self.typeface, self.letter_spacing)

	def draw(self, image: Image.Image, position: tuple[float, float], fill: str):
		"""Draw with the left edge and vertical middle at `position`."""
		x, y = position
		for is_emoji, run in self.runs():
			if is_emoji:
				self.draw_emoji(image, (x, y), run)
			else:
				self.draw_letters(ImageDraw.Draw(image), (x, y), run, fill)
			x += self.run_width(is_emoji, run)

	def draw_letters(self, draw: ImageDraw.ImageDraw, position: tuple[float, float], run: str, fill: str):
		# Pillow has no letter-spacing; placing each glyph at the kerned prefix width keeps kerning
		x, y = position
		for index, character in enumerate(run):
			offset = self.typeface.getlength(run[:index]) + self.letter_spacing * index
			draw.text((x + offset, y), character, font=self.typeface, fill=fill, anchor="lm")

	def draw_emoji(self, image: Image.Image, position: tuple[float, float], run: str):
		width, height = emoji_font().getbbox(run)[2:]
		if not width:
			return
		glyphs = Image.new("RGBA", (width, height))
		ImageDraw.Draw(glyphs).text((0, 0), run, font=emoji_font(), embedded_color=True)
		size = (round(width * self.emoji_scale), round(height * self.emoji_scale))
		glyphs = glyphs.resize(size, Image.LANCZOS)
		image.paste(glyphs, (round(position[0]), round(position[1] - size[1] / 2)), glyphs)
