import frappe

from buzz.api.events import services
from buzz.api.events.schemas import CreatedEvent, EventDetail, MyEventsResponse, NewEvent


@frappe.whitelist()
def get_my_events() -> MyEventsResponse:
	"""Events hosted by the session user's teams, plus events they hold a ticket to."""
	return services.my_events()


@frappe.whitelist()
def get_event(event: str) -> EventDetail:
	"""One event for the manage page, for someone who can edit it."""
	return services.event_detail(event)


@frappe.whitelist(methods=["POST"])
def create_event(event: NewEvent) -> CreatedEvent:
	return services.create_event(event)
