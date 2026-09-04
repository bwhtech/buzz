import frappe

from buzz.api.events import services
from buzz.api.events.schemas import (
	CreatedEvent,
	EventDetail,
	EventGuestsResponse,
	MyEventFilters,
	MyEventsResponse,
	NewEvent,
	RegistrationTrend,
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
def get_event_guests(
	event: str,
	search: str | None = None,
	ticket_types: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = services.GUESTS_PAGE_SIZE,
) -> EventGuestsResponse:
	"""One page of the people holding a submitted ticket to an event, with their add-ons.

	`ticket_types` is comma-joined rather than a list: a GET query string carries one, and
	it is the same string the dashboard keeps the filter in.
	"""
	return services.event_guests(event, search, ticket_types, order, start, limit)


@frappe.whitelist()
def get_event_registration_trend(event: str, days: int = services.TREND_DAYS) -> RegistrationTrend:
	"""Registrations per day for an event, for the card above its guest list."""
	return services.registration_trend(event, days)


@frappe.whitelist()
def check_event_route(route: str, event: str | None = None) -> RouteAvailability:
	"""Whether an event can take this route. `event` is the one being edited, if any."""
	return services.route_availability(route, event)


@frappe.whitelist(methods=["POST"])
def create_event(event: NewEvent) -> CreatedEvent:
	return services.create_event(event)
