from urllib.parse import quote

import frappe
import requests

from buzz.api.maps.exceptions import CannotAddVenues, PlaceSearchFailed, PlaceSearchNotEnabled
from buzz.api.maps.schemas import MapLinkLocation, PlacePrediction
from buzz.events.doctype.event_venue.map_link import read_map_link
from buzz.www.event.venue_map import google_maps_url

AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
REQUEST_TIMEOUT_SECONDS = 5


def place_search_enabled() -> bool:
	settings = frappe.get_cached_doc("Buzz Settings")
	return bool(settings.google_maps_enabled and settings.google_places_api_key)


def locate_map_link(link: str) -> MapLinkLocation:
	"""Read a pasted map link the way saving a venue would, without saving anything."""
	if not frappe.has_permission("Event Venue", "create"):
		CannotAddVenues.throw()
	if embed_url := google_maps_url(link):
		return MapLinkLocation(embed_url=embed_url)
	place = read_map_link(link)
	latitude, longitude = place.coordinates or (None, None)
	return MapLinkLocation(latitude=latitude, longitude=longitude, name=place.name, address=place.address)


class GooglePlaces:
	"""Google Places calls made with the site's secret key, for someone who can add venues."""

	def __init__(self):
		if not frappe.has_permission("Event Venue", "create"):
			CannotAddVenues.throw()
		if not place_search_enabled():
			PlaceSearchNotEnabled.throw()
		self.api_key = frappe.get_cached_doc("Buzz Settings").get_password("google_places_api_key")

	def search(self, query: str, session_token: str) -> list[PlacePrediction]:
		if not query.strip():
			return []
		data = self.request("POST", AUTOCOMPLETE_URL, json={"input": query, "sessionToken": session_token})
		return [
			prediction_of(suggestion["placePrediction"])
			for suggestion in data.get("suggestions", [])
			if "placePrediction" in suggestion
		]

	def save_as_venue(self, team: str, place_id: str, name: str, session_token: str) -> str:
		existing = frappe.db.exists("Event Venue", {"team": team, "google_place_id": place_id})
		if existing:
			frappe.has_permission("Event Venue", "read", existing, throw=True)
			return existing
		venue = frappe.get_doc(
			{
				"doctype": "Event Venue",
				"team": team,
				"venue_name": name,
				"address": self.address_of(place_id, session_token) or name,
				"google_place_id": place_id,
			}
		)
		return venue.insert().name

	def address_of(self, place_id: str, session_token: str) -> str | None:
		# Only the address is asked for: the name came with the prediction, and the place id
		# is the one thing Google lets a site keep for good.
		place = self.request(
			"GET",
			DETAILS_URL.format(place_id=quote(place_id, safe="")),
			params={"sessionToken": session_token},
			headers={"X-Goog-FieldMask": "id,formattedAddress"},
		)
		return place.get("formattedAddress")

	def request(self, method: str, url: str, headers: dict | None = None, **options) -> dict:
		try:
			response = requests.request(
				method,
				url,
				headers={"X-Goog-Api-Key": self.api_key, **(headers or {})},
				timeout=REQUEST_TIMEOUT_SECONDS,
				**options,
			)
			response.raise_for_status()
		except requests.RequestException as error:
			# Google's answer names the cause (disabled API, key restriction, billing); it never holds the key
			answer = error.response.text if error.response is not None else str(error)
			frappe.log_error("Google Places request failed", answer)
			PlaceSearchFailed.throw()
		return response.json()


def prediction_of(place: dict) -> PlacePrediction:
	text = place.get("structuredFormat", {})
	return PlacePrediction(
		place_id=place["placeId"],
		name=text.get("mainText", {}).get("text") or place["text"]["text"],
		address=text.get("secondaryText", {}).get("text"),
	)
