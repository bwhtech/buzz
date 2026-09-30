import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.maps import services
from buzz.api.maps.schemas import PlacePrediction


@frappe.whitelist()
@rate_limit(limit=120, seconds=60)
def search_places(query: str, session_token: str) -> list[PlacePrediction]:
	"""Google Maps places matching what the organiser typed into the venue picker."""
	return services.GooglePlaces().search(query, session_token)
