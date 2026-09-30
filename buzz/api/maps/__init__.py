import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.maps import services
from buzz.api.maps.schemas import MapLinkLocation, PlacePrediction


@frappe.whitelist()
@rate_limit(limit=120, seconds=60)
def search_places(query: str, session_token: str) -> list[PlacePrediction]:
	"""Google Maps places matching what the organiser typed into the venue picker."""
	return services.GooglePlaces().search(query, session_token)


@frappe.whitelist(methods=["POST"])
def add_place_as_venue(team: str, place_id: str, name: str, session_token: str) -> str:
	"""Save a place picked from the search as one of the team's venues, answering with its name."""
	return services.GooglePlaces().save_as_venue(team, place_id, name, session_token)


@frappe.whitelist()
@rate_limit(limit=30, seconds=60)
def locate_map_link(link: str) -> MapLinkLocation:
	"""Where a pasted Google Maps or OpenStreetMap link points, for the add-venue preview."""
	return services.locate_map_link(link)
