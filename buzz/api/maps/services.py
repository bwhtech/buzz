import frappe
import requests

from buzz.api.maps.exceptions import CannotAddVenues, PlaceSearchFailed, PlaceSearchNotEnabled
from buzz.api.maps.schemas import PlacePrediction

AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
REQUEST_TIMEOUT_SECONDS = 5


def place_search_enabled() -> bool:
	settings = frappe.get_cached_doc("Buzz Settings")
	return bool(settings.google_maps_enabled and settings.google_places_api_key)


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
		data = self.post(AUTOCOMPLETE_URL, {"input": query, "sessionToken": session_token})
		return [
			prediction_of(suggestion["placePrediction"])
			for suggestion in data.get("suggestions", [])
			if "placePrediction" in suggestion
		]

	def post(self, url: str, body: dict) -> dict:
		try:
			response = requests.post(
				url, json=body, headers={"X-Goog-Api-Key": self.api_key}, timeout=REQUEST_TIMEOUT_SECONDS
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
