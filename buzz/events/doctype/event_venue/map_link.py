import re
from typing import NamedTuple
from urllib.parse import ParseResult, parse_qs, unquote_plus, urlparse

import requests
from frappe.utils import get_url

GOOGLE_HOST = re.compile(r"(^|\.)google\.[a-z.]+$")
GOOGLE_SHORT_LINK_HOSTS = {"maps.app.goo.gl", "goo.gl"}
OPEN_STREET_MAP_HOSTS = {"www.openstreetmap.org", "openstreetmap.org", "www.osm.org", "osm.org"}
NUMBER = r"(-?\d+(?:\.\d+)?)"
# `!3d…!4d…` is the place itself; `@…` is only where the map happened to be centred.
GOOGLE_PLACE = re.compile(rf"!3d{NUMBER}!4d{NUMBER}")
GOOGLE_VIEW = re.compile(rf"@{NUMBER},{NUMBER}")
GOOGLE_PLACE_NAME = re.compile(r"/maps/place/([^/@]+)")
OPEN_STREET_MAP_VIEW = re.compile(rf"map=\d+/{NUMBER}/{NUMBER}")
OPEN_STREET_MAP_OBJECT = re.compile(r"^/(node|way|relation)/(\d+)")
OPEN_STREET_MAP_SHORT_LINK = re.compile(r"^/go/([A-Za-z0-9_~@-]+)")
SHORT_LINK_DIGITS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_~"
NOMINATIM_LOOKUP_URL = "https://nominatim.openstreetmap.org/lookup"
REQUEST_TIMEOUT_SECONDS = 5

Coordinates = tuple[float, float]


class MapLinkPlace(NamedTuple):
	"""What a pasted map link says about a place; every part may be missing."""

	coordinates: Coordinates | None = None
	name: str | None = None
	address: str | None = None


def coordinates_of(link: str | None) -> Coordinates | None:
	"""Latitude and longitude carried by a Google Maps or OpenStreetMap link, if any."""
	return read_map_link(link).coordinates


def read_map_link(link: str | None) -> MapLinkPlace:
	url = resolved_url(link)
	host = url.hostname or ""
	if host in OPEN_STREET_MAP_HOSTS:
		return open_street_map_place(url)
	if GOOGLE_HOST.search(host):
		return MapLinkPlace(google_coordinates(url), google_place_name(url))
	return MapLinkPlace()


def resolved_url(link: str | None) -> ParseResult:
	"""The link as a URL, with a Google short link swapped for the full one it stands for."""
	url = urlparse((link or "").strip())
	if url.hostname in GOOGLE_SHORT_LINK_HOSTS:
		url = urlparse(full_google_link(url.geturl()) or "")
	return url


def full_google_link(short_link: str) -> str | None:
	# One hop, to a host named above, and only the redirect target is read: a pasted link
	# must not be able to point the server at an address of its choosing.
	try:
		response = requests.get(
			short_link.replace("http://", "https://", 1),
			allow_redirects=False,
			timeout=REQUEST_TIMEOUT_SECONDS,
		)
	except requests.RequestException:
		return None
	return response.headers.get("Location")


def google_coordinates(url: ParseResult) -> Coordinates | None:
	link = url.geturl()
	match = GOOGLE_PLACE.search(link) or GOOGLE_VIEW.search(link)
	return valid_coordinates(*match.groups()) if match else None


def google_place_name(url: ParseResult) -> str | None:
	match = GOOGLE_PLACE_NAME.search(url.path)
	return unquote_plus(match.group(1)) if match else None


def open_street_map_place(url: ParseResult) -> MapLinkPlace:
	if map_object := OPEN_STREET_MAP_OBJECT.match(url.path):
		return open_street_map_object(*map_object.groups())
	if short_link := OPEN_STREET_MAP_SHORT_LINK.match(url.path):
		return MapLinkPlace(short_link_coordinates(short_link.group(1)))
	return MapLinkPlace(open_street_map_coordinates(url))


def open_street_map_coordinates(url: ParseResult) -> Coordinates | None:
	query = parse_qs(url.query)
	if "mlat" in query and "mlon" in query:
		return valid_coordinates(query["mlat"][0], query["mlon"][0])
	match = OPEN_STREET_MAP_VIEW.search(url.fragment)
	return valid_coordinates(*match.groups()) if match else None


def short_link_coordinates(code: str) -> Coordinates | None:
	"""Undo OpenStreetMap's `/go/` code: each character holds 3 bits of longitude and 3 of latitude."""
	x = y = bits = 0
	for character in code.replace("@", "~"):
		digit = SHORT_LINK_DIGITS.find(character)
		if digit < 0:
			continue  # "-" only refines the zoom
		for shift in (5, 3, 1):
			x = (x << 1) | ((digit >> shift) & 1)
			y = (y << 1) | ((digit >> (shift - 1)) & 1)
		bits += 3
	if not bits or bits > 32:
		return None
	longitude = (x << (32 - bits)) * 360 / 2**32 - 180
	latitude = (y << (32 - bits)) * 180 / 2**32 - 90
	return round(latitude, 6), round(longitude, 6)


def open_street_map_object(kind: str, number: str) -> MapLinkPlace:
	"""A node, way or relation link names a map object; Nominatim says where and what it is."""
	try:
		response = requests.get(
			NOMINATIM_LOOKUP_URL,
			params={"osm_ids": f"{kind[0].upper()}{number}", "format": "jsonv2"},
			# Nominatim's usage policy asks each application to say who it is
			headers={"User-Agent": f"Buzz event venues ({get_url()})"},
			timeout=REQUEST_TIMEOUT_SECONDS,
		)
		response.raise_for_status()
		found = response.json()
	except (requests.RequestException, ValueError):
		return MapLinkPlace()
	if not found:
		return MapLinkPlace()
	place = found[0]
	return MapLinkPlace(
		valid_coordinates(place.get("lat"), place.get("lon")),
		place.get("name") or None,
		place.get("display_name") or None,
	)


def valid_coordinates(latitude: str | None, longitude: str | None) -> Coordinates | None:
	try:
		point = float(latitude), float(longitude)
	except (TypeError, ValueError):
		return None
	return point if abs(point[0]) <= 90 and abs(point[1]) <= 180 else None
