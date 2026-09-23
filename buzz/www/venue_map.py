import html
import re
from urllib.parse import urlencode, urlparse

GOOGLE_MAPS_HOSTS = {"www.google.com", "maps.google.com"}
IFRAME_SOURCE = re.compile(r"""src\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
MAP_SPAN_DEGREES = 0.01


def venue_map_url(venue) -> str | None:
	if venue.type == "Embed Google Maps":
		return google_maps_url(venue.google_maps_embed_code)
	return open_street_map_url(venue.latitude, venue.longitude)


def google_maps_url(embed_code: str | None) -> str | None:
	# The embed code is raw markup; only a Google Maps embed URL survives, never the markup itself
	match = IFRAME_SOURCE.search(embed_code or "")
	url = html.unescape(match.group(1) if match else (embed_code or "").strip())
	parsed = urlparse(url)
	if (
		parsed.scheme == "https"
		and parsed.hostname in GOOGLE_MAPS_HOSTS
		and parsed.path.startswith("/maps/embed")
	):
		return url
	return None


def open_street_map_url(latitude: float | None, longitude: float | None) -> str | None:
	if not (latitude and longitude):
		return None
	box = [
		longitude - MAP_SPAN_DEGREES,
		latitude - MAP_SPAN_DEGREES,
		longitude + MAP_SPAN_DEGREES,
		latitude + MAP_SPAN_DEGREES,
	]
	query = urlencode(
		{
			"bbox": ",".join([str(edge) for edge in box]),
			"layer": "mapnik",
			"marker": f"{latitude},{longitude}",
		}
	)
	return f"https://www.openstreetmap.org/export/embed.html?{query}"
