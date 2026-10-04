"""Python port of buzz/public/js/event_banner.ts, for images drawn on the server."""

import math

from PIL import Image, ImageDraw

LINE_WIDTH = 2


def random_from(seed: str):
	"""FNV-1a seed, then xorshift32, matching event_banner.ts."""
	state = 2166136261
	for character in seed:
		state = ((state ^ ord(character)) * 16777619) & 0xFFFFFFFF

	def next_draw() -> float:
		nonlocal state
		state ^= (state << 13) & 0xFFFFFFFF
		state ^= state >> 17
		state ^= (state << 5) & 0xFFFFFFFF
		return state / 4294967296

	return next_draw


def between(draw: float, low: float, high: float) -> float:
	return low + draw * (high - low)


def off_centre(draw: float) -> float:
	return between(draw * 2, -10, 30) if draw < 0.5 else between(draw * 2 - 1, 70, 110)


def banner_pattern(seed: str) -> dict:
	"""Port of bannerPattern() in event_banner.ts: percentages of the box, gap in px."""
	next_draw = random_from(seed)
	return {
		"origin_x": round(off_centre(next_draw())),
		"origin_y": round(off_centre(next_draw())),
		"radius_x": round(between(next_draw(), 55, 110)),
		"radius_y": round(between(next_draw(), 55, 110)),
		"gap": float(f"{between(next_draw(), 18, 26):.1f}"),
	}


def rings_banner(seed: str, size: tuple, line: str, surface: str) -> Image.Image:
	# Drawn at 2x and scaled down: 2px ellipse outlines alias badly at 1x
	scale = 2
	width, height = size[0] * scale, size[1] * scale
	pattern = banner_pattern(seed or "Untitled")
	origin_x, origin_y = pattern["origin_x"] / 100 * width, pattern["origin_y"] / 100 * height
	squash = (pattern["radius_y"] / 100 * height) / (pattern["radius_x"] / 100 * width)
	gap, stroke = pattern["gap"] * scale, LINE_WIDTH * scale
	farthest = max(math.hypot(x - origin_x, (y - origin_y) / squash) for x in (0, width) for y in (0, height))
	image = Image.new("RGB", (width, height), surface)
	draw = ImageDraw.Draw(image)
	for index in range(int(farthest / gap) + 2):
		outer = index * gap + stroke
		box = (origin_x - outer, origin_y - outer * squash, origin_x + outer, origin_y + outer * squash)
		draw.ellipse(box, outline=line, width=stroke)
	return image.resize(size, Image.LANCZOS)
