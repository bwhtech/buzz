from dataclasses import dataclass

# The dot assets share the team map's equirectangular coordinates: x = longitude + 180,
# y = 90 - latitude. Land spans y 6 to 146.
WORLD_TOP, WORLD_BOTTOM, WORLD_WIDTH = 6, 146, 360
ASPECT_RATIO = 1.6
# One country on its own is too few dots to read as land.
MINIMUM_VIEW_WIDTH = 60
PADDING = 0.15
# Wider than this, the fine 1.2° dots blur together at sidebar size.
COARSE_DOTS_ABOVE_WIDTH = 150
FINE_DOTS = {"url": "/assets/buzz/images/world-dots.svg#world-dots", "grid": 1.2}
COARSE_DOTS = {"url": "/assets/buzz/images/world-dots-coarse.svg#world-dots-coarse", "grid": 3}
DOT_SHARE_OF_GRID = 0.45


@dataclass
class View:
	x: float
	y: float
	width: float
	height: float

	def __str__(self) -> str:
		return " ".join(str(round(value, 2)) for value in (self.x, self.y, self.width, self.height))


class DotMap:
	"""A land-dot map framed around a set of (latitude, longitude) pins."""

	def __init__(self, coordinates: list[tuple[float, float]]):
		self.points = [(longitude + 180, 90 - latitude) for latitude, longitude in coordinates]
		self.view = self.frame()
		self.dots = COARSE_DOTS if self.view.width > COARSE_DOTS_ABOVE_WIDTH else FINE_DOTS

	@property
	def dots_url(self) -> str:
		return self.dots["url"]

	@property
	def dot_width(self) -> float:
		return self.dots["grid"] * DOT_SHARE_OF_GRID

	def frame(self) -> View:
		xs, ys = [x for x, _ in self.points], [y for _, y in self.points]
		span = max(max(xs) - min(xs), (max(ys) - min(ys)) * ASPECT_RATIO) * (1 + 2 * PADDING)
		width = min(max(span, MINIMUM_VIEW_WIDTH), WORLD_WIDTH)
		height = width / ASPECT_RATIO
		x = clamp((max(xs) + min(xs) - width) / 2, 0, WORLD_WIDTH - width)
		y = clamp((max(ys) + min(ys) - height) / 2, WORLD_TOP, WORLD_BOTTOM - height)
		return View(x, y, width, height)

	def pin(self, latitude: float, longitude: float) -> dict[str, float]:
		"""A pin's place on the map, as percentages from its top left corner."""
		x = (longitude + 180 - self.view.x) / self.view.width
		y = (90 - latitude - self.view.y) / self.view.height
		return {"x": round(x * 100, 2), "y": round(y * 100, 2)}


def clamp(value: float, low: float, high: float) -> float:
	# A view taller than the land centres on it rather than clamping past both edges.
	return (low + high) / 2 if high < low else min(max(value, low), high)
