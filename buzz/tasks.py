import frappe
from frappe.utils import today

from buzz.api.booking.cache import invalidate_event_booking_cache


def unpublish_ticket_types_after_last_date():
	rows = frappe.get_all(
		"Event Ticket Type",
		filters={"is_published": True, "auto_unpublish_after": ("<", today())},
		fields=["name", "event"],
	)
	if not rows:
		return
	frappe.db.set_value(
		"Event Ticket Type",
		{"name": ("in", [row.name for row in rows])},
		"is_published",
		False,
	)
	for row in rows:
		frappe.clear_document_cache("Event Ticket Type", str(row.name))
	for event_id in {str(row.event) for row in rows if row.event}:
		invalidate_event_booking_cache(event_id)
