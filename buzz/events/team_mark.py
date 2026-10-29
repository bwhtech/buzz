"""The team's logo on the rounded tile that straddles the share image's band."""

from collections import Counter

from PIL import Image, ImageDraw, ImageFilter

from buzz.events.og_image import uploaded_image
from buzz.events.og_text import font

LOGO_SIZE, LOGO_RADIUS, LOGO_RING = 136, 30, 6
MARK_SIZE = LOGO_SIZE + 2 * LOGO_RING
# A wordmark that spans the tile would be clipped by its rounded corner
LOGO_INSET = 12
MONOGRAM_SIZE = 60
MONOGRAM_TILE, MONOGRAM_INK = "#ececec", "#6b6b6b"
DARK_LOGO_LUMA = 90
SHADOW_MARGIN, SHADOW_OFFSET, SHADOW_BLUR, SHADOW_ALPHA = 24, 4, 8, 26
SCALE = 2  # marks and shadows are drawn at 2x and scaled down


class TeamMark:
	"""Drawn from the team's logo, or from the first letter of its name when it has none."""

	def __init__(self, team, colours: dict, top: int):
		self.team = team
		self.colours = colours
		self.top = top

	def draw(self, image: Image.Image, left: int):
		avatar = self.avatar()
		image.paste(avatar, (left - SHADOW_MARGIN, self.top - SHADOW_MARGIN), avatar)

	def avatar(self) -> Image.Image:
		side = (MARK_SIZE + 2 * SHADOW_MARGIN) * SCALE
		margin = SHADOW_MARGIN * SCALE
		canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
		canvas.alpha_composite(self.shadow(margin, side))
		canvas.alpha_composite(self.tile(), (margin, margin))
		return canvas.resize((side // SCALE, side // SCALE), Image.LANCZOS)

	def shadow(self, margin: int, side: int) -> Image.Image:
		shadow = Image.new("RGBA", (side, side), (0, 0, 0, 0))
		ImageDraw.Draw(shadow).rounded_rectangle(
			(
				margin,
				margin + SHADOW_OFFSET * SCALE,
				margin + MARK_SIZE * SCALE,
				margin + (MARK_SIZE + SHADOW_OFFSET) * SCALE,
			),
			radius=(LOGO_RADIUS + LOGO_RING) * SCALE,
			fill=(17, 17, 17, SHADOW_ALPHA),
		)
		return shadow.filter(ImageFilter.GaussianBlur(SHADOW_BLUR * SCALE))

	def tile(self) -> Image.Image:
		side, ring = MARK_SIZE * SCALE, LOGO_RING * SCALE
		tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
		ImageDraw.Draw(tile).rounded_rectangle(
			(0, 0, side - 1, side - 1),
			radius=(LOGO_RADIUS + LOGO_RING) * SCALE,
			fill=self.colours["page-bg"],
		)
		mark = self.mark()
		mask = Image.new("L", mark.size, 0)
		ImageDraw.Draw(mask).rounded_rectangle(
			(0, 0, mark.width - 1, mark.height - 1), radius=LOGO_RADIUS * SCALE, fill=255
		)
		tile.paste(mark, (ring, ring), mask)
		return tile

	def mark(self) -> Image.Image:
		"""The whole logo is scaled into the tile, so a wide or tall mark is never cropped."""
		inner = LOGO_SIZE * SCALE
		logo = uploaded_image(self.team.logo)
		if logo is None:
			return self.monogram(inner)
		logo = logo.convert("RGBA")
		mark = Image.new("RGBA", (inner, inner), self.mark_background(logo))
		scale = (inner - 2 * LOGO_INSET * SCALE) / max(logo.width, logo.height)
		fit = (max(1, round(logo.width * scale)), max(1, round(logo.height * scale)))
		resized = logo.resize(fit, Image.LANCZOS)
		mark.paste(resized, ((inner - fit[0]) // 2, (inner - fit[1]) // 2), resized)
		return mark

	def mark_background(self, logo: Image.Image) -> str:
		# A transparent or dark mark needs white behind it; a flat light mark carries its own
		# colour, which fills the letterboxing invisibly
		if logo.getchannel("A").getextrema()[0] < 255:
			return self.colours["page-bg"]
		if logo.convert("L").resize((1, 1), Image.BOX).getpixel((0, 0)) < DARK_LOGO_LUMA:
			return self.colours["page-bg"]
		return edge_colour(logo)

	def monogram(self, size: int) -> Image.Image:
		mark = Image.new("RGBA", (size, size), MONOGRAM_TILE)
		letter = self.team.team_name[:1].upper() or "?"
		typeface = font("SemiBold", MONOGRAM_SIZE * SCALE)
		left, top, right, bottom = typeface.getbbox(letter, anchor="ls")
		# Centre the letter's ink, not the em box
		ImageDraw.Draw(mark).text(
			((size - right - left) / 2, (size - bottom - top) / 2),
			letter,
			font=typeface,
			fill=MONOGRAM_INK,
			anchor="ls",
		)
		return mark


def edge_colour(logo: Image.Image) -> str:
	"""The most common colour on the logo's border, used to fill around it."""
	pixels = logo.convert("RGB")
	width, height = pixels.size
	border = [pixels.getpixel((x, 0)) for x in range(width)]
	border += [pixels.getpixel((x, height - 1)) for x in range(width)]
	border += [pixels.getpixel((0, y)) for y in range(height)]
	border += [pixels.getpixel((width - 1, y)) for y in range(height)]
	return "#%02x%02x%02x" % Counter(border).most_common(1)[0][0]
