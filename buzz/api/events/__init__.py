import frappe

from buzz.api.events import services
from buzz.api.events.schemas import MyEventsResponse


@frappe.whitelist()
def get_my_events() -> MyEventsResponse:
	"""Events hosted by the session user's teams, plus events they hold a ticket to."""
	return services.my_events()
