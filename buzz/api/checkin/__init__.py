import frappe

from buzz.api.checkin.schemas import CheckinEvent, CheckinResponse
from buzz.api.checkin.services import CheckinService, checkin_events, ensure_can_check_in
from buzz.api.events.schemas import EventGuestsResponse
from buzz.api.events.services import GUESTS_PAGE_SIZE, event_guests


@frappe.whitelist()
def validate_ticket_for_checkin(ticket_id: str) -> CheckinResponse:
	return CheckinService(ticket_id).validate()


@frappe.whitelist(methods=["POST"])
def checkin_ticket(ticket_id: str) -> CheckinResponse:
	return CheckinService(ticket_id).checkin()


@frappe.whitelist(methods=["POST"])
def undo_checkin(ticket_id: str) -> CheckinResponse:
	return CheckinService(ticket_id).undo_checkin()


@frappe.whitelist()
def get_checkin_events() -> list[CheckinEvent]:
	return checkin_events()


@frappe.whitelist()
def get_checkin_guests(
	event: str,
	search: str | None = None,
	checked_in: str | None = None,
	start: int = 0,
	limit: int = GUESTS_PAGE_SIZE,
) -> EventGuestsResponse:
	"""The guest list, for someone who can check its guests in."""
	ensure_can_check_in(event)
	return event_guests(event, search, start=start, limit=limit, checked_in=checked_in)
