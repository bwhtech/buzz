import time

import frappe
import requests
from frappe.utils import flt, get_url

from buzz.events.doctype.event_venue.map_link import REQUEST_TIMEOUT_SECONDS

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
# Nominatim's usage policy allows one request a second.
REQUEST_INTERVAL_SECONDS = 1
CITY_KEYS = ("city", "town", "village", "municipality")
# Nominatim finds nothing for many street-level addresses, Google's especially; their last
# few parts (locality, city, state, country) still place the venue well enough for a pin.
ADDRESS_ENDINGS = (4, 3)


def has_coordinates(venue) -> bool:
	return bool(flt(venue.latitude) and flt(venue.longitude))


def needs_geocoding(venue) -> bool:
	is_complete = has_coordinates(venue) and venue.city and venue.venue_country
	return bool(venue.address or has_coordinates(venue)) and not is_complete


def enqueue_geocode(venue_name: str) -> None:
	frappe.enqueue(
		"buzz.events.doctype.event_venue.geocode.geocode_venue",
		venue_name=venue_name,
		job_id=f"geocode_venue::{venue_name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def geocode_venue(venue_name: str) -> None:
	VenueGeocoder(frappe.get_doc("Event Venue", venue_name)).fill()


def geocode_all_venues() -> None:
	for venue_name in venues_to_geocode():
		geocode_venue(venue_name)
		time.sleep(REQUEST_INTERVAL_SECONDS)


def venues_to_geocode() -> list[str]:
	fields = ["name", "address", "latitude", "longitude", "city", "venue_country"]
	return [venue.name for venue in frappe.get_all("Event Venue", fields=fields) if needs_geocoding(venue)]


def address_queries(address: str) -> list[str]:
	"""The full address, then its shorter endings, without repeats."""
	parts = [part.strip() for part in address.split(",") if part.strip()]
	endings = [", ".join(parts[-size:]) for size in ADDRESS_ENDINGS if len(parts) > size]
	return list(dict.fromkeys([address, *endings]))


def country_with_code(code: str | None) -> str | None:
	return frappe.db.get_value("Country", {"code": code.lower()}) if code else None


class VenueGeocoder:
	"""Fills a venue's empty coordinates, city and country from OpenStreetMap Nominatim."""

	def __init__(self, venue):
		self.venue = venue

	def fill(self) -> None:
		place = self.lookup()
		if not place or "error" in place:
			return
		venue, address = self.venue, place.get("address") or {}
		if not has_coordinates(venue):
			venue.latitude, venue.longitude = flt(place.get("lat")), flt(place.get("lon"))
		venue.city = venue.city or next((address[key] for key in CITY_KEYS if address.get(key)), None)
		venue.venue_country = venue.venue_country or country_with_code(address.get("country_code"))
		venue.flags.geocoded = True
		venue.save(ignore_permissions=True)

	def lookup(self) -> dict | None:
		if has_coordinates(self.venue):
			# Zoom 10 answers at city level rather than with the nearest building.
			return self.request(
				"reverse", {"lat": self.venue.latitude, "lon": self.venue.longitude, "zoom": 10}
			)
		for index, query in enumerate(address_queries(self.venue.address)):
			if index:
				time.sleep(REQUEST_INTERVAL_SECONDS)
			if results := self.request("search", {"q": query, "limit": 1}):
				return results[0]
		return None

	def request(self, endpoint: str, params: dict):
		try:
			response = requests.get(
				f"{NOMINATIM_URL}/{endpoint}",
				params={**params, "format": "jsonv2", "addressdetails": 1},
				# Nominatim's usage policy asks each application to say who it is
				headers={"User-Agent": f"Buzz event venues ({get_url()})"},
				timeout=REQUEST_TIMEOUT_SECONDS,
			)
			response.raise_for_status()
			return response.json()
		except (requests.RequestException, ValueError):
			frappe.log_error(f"Geocoding venue {self.venue.name} failed")
			return None
