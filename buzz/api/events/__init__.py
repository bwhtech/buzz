import frappe

from buzz.api.events import services
from buzz.api.events.schemas import (
	CreatedEvent,
	EventDetail,
	EventGuestsResponse,
	MyEventFilters,
	MyEventsResponse,
	NewEvent,
	RouteAvailability,
)


@frappe.whitelist()
def get_my_events(filters: dict | str | None = None) -> MyEventsResponse:
	"""Events hosted by the session user's teams, plus events they hold a ticket to.

	`filters` arrives as JSON rather than a model: a nested object cannot ride on a GET
	query string, and frappe validates a model-annotated argument with validate_python,
	which does not parse JSON. Same shape as submit_custom_form's `data`.
	"""
	return services.my_events(MyEventFilters.model_validate(frappe.parse_json(filters or {})))


@frappe.whitelist()
def get_event(event: str) -> EventDetail:
	"""One event for the manage page, for someone who can edit it."""
	return services.event_detail(event)


@frappe.whitelist()
def get_event_guests(event: str) -> EventGuestsResponse:
	"""Everyone holding a submitted ticket to an event, with their add-ons."""
	return services.event_guests(event)


@frappe.whitelist()
def check_event_route(route: str, event: str | None = None) -> RouteAvailability:
	"""Whether an event can take this route. `event` is the one being edited, if any."""
	return services.route_availability(route, event)


@frappe.whitelist(methods=["POST"])
def create_event(event: NewEvent) -> CreatedEvent:
	return services.create_event(event)
