import frappe
from frappe.utils import today

from buzz.api.booking.services import has_event_ended
from buzz.ticketing.approval import PENDING_APPROVAL


def unpublish_ticket_types_after_last_date():
	frappe.db.set_value(
		"Event Ticket Type",
		{"is_published": True, "auto_unpublish_after": ("<", today())},
		"is_published",
		False,
	)


def expire_pending_approval_requests():
	"""Requests still waiting once their event has ended can never be approved."""
	pending = frappe.get_all("Event Booking", filters=PENDING_APPROVAL, fields=["name", "event"])
	ended_events = {
		event
		for event in {row.event for row in pending}
		if has_event_ended(frappe.get_cached_doc("Buzz Event", event))
	}
	for row in pending:
		if row.event in ended_events:
			frappe.get_doc("Event Booking", row.name).discard_as("Expired")
