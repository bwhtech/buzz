from urllib.parse import urlencode, urlparse

import frappe

from buzz.api.schemas import APIResponse

LOCATION_FIELDS = ("name", "venue_name", "address", "latitude", "longitude", "google_place_id", "map_link")
GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/"


class VenueLocation(APIResponse):
	venue_name: str
	label: str | None = None
	address: str | None = None
	latitude: float | None = None
	longitude: float | None = None
	# Opens the place in Google Maps
	map_link: str | None = None


class VenueDetails(APIResponse):
	name: str
	venue_name: str
	address: str | None = None
	map_link: str | None = None
	has_multiple_locations: bool = False
	# A single venue lists itself
	locations: list[VenueLocation]


def venue_details(venue: str | None) -> VenueDetails | None:
	row = venue and frappe.db.get_value(
		"Event Venue", venue, [*LOCATION_FIELDS, "has_multiple_locations"], as_dict=True
	)
	if not row:
		return None
	if row.has_multiple_locations:
		return VenueDetails(
			name=row.name,
			venue_name=row.venue_name,
			has_multiple_locations=True,
			locations=group_locations(row.name),
		)
	location = location_of(row)
	return VenueDetails(
		name=row.name,
		venue_name=row.venue_name,
		address=row.address,
		map_link=location.map_link,
		locations=[location],
	)


def group_locations(group: str) -> list[VenueLocation]:
	location, venue = frappe.qb.DocType("Event Venue Location"), frappe.qb.DocType("Event Venue")
	rows = (
		frappe.qb.from_(location)
		.join(venue)
		.on(venue.name == location.venue)
		.select(location.label, *[venue[field] for field in LOCATION_FIELDS])
		.where((location.parent == group) & (location.parenttype == "Event Venue"))
		.orderby(location.idx)
		.run(as_dict=True)
	)
	return [location_of(row) for row in rows]


def location_of(row) -> VenueLocation:
	return VenueLocation(
		venue_name=row.venue_name,
		label=row.get("label"),
		address=row.address,
		latitude=row.latitude or None,
		longitude=row.longitude or None,
		map_link=map_link_of(row),
	)


def map_link_of(venue) -> str | None:
	# The organiser's own link wins. Pasted embed code is markup, not somewhere to go.
	if urlparse(venue.map_link or "").scheme in ("http", "https"):
		return venue.map_link
	if venue.google_place_id:
		place = {"api": 1, "query": venue.venue_name, "query_place_id": venue.google_place_id}
		return f"{GOOGLE_MAPS_SEARCH_URL}?{urlencode(place)}"
	query = f"{venue.latitude},{venue.longitude}" if venue.latitude and venue.longitude else venue.address
	return f"{GOOGLE_MAPS_SEARCH_URL}?{urlencode({'api': 1, 'query': query})}" if query else None
