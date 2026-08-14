import frappe

from buzz.api.events import services
from buzz.api.events.schemas import CreatedEvent, MyEventsResponse, NewEvent


@frappe.whitelist()
def get_my_events() -> MyEventsResponse:
	"""Events hosted by the session user's teams, plus events they hold a ticket to."""
	return services.my_events()


@frappe.whitelist(methods=["POST"])
def create_event(event: NewEvent) -> CreatedEvent:
	return services.create_event(event)
