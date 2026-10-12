# The latitudes the dot map's viewBox (0 6 360 140) shows; it is an equirectangular map, so
# a pin's position is linear in its coordinates.
LATITUDE_TOP = 84
LATITUDE_BOTTOM = -56


def pin_position(latitude: float, longitude: float) -> dict[str, float]:
	"""A pin's place on the dot map, as percentages from its top left corner."""
	x = (longitude + 180) / 360
	y = (LATITUDE_TOP - latitude) / (LATITUDE_TOP - LATITUDE_BOTTOM)
	return {"x": as_percentage(x), "y": as_percentage(y)}


def as_percentage(fraction: float) -> float:
	return round(min(max(fraction, 0), 1) * 100, 2)
