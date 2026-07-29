import frappe
from frappe.utils import days_diff, today

TRANSFER = "allow_transfer_ticket_before_event_start_days"
ADD_ON_CHANGE = "allow_add_ons_change_before_event_start_days"
CANCELLATION = "allow_ticket_cancellation_request_before_event_start_days"

DEFAULT_CUTOFF_DAYS = 7


def is_window_open(event_id: str | int, cutoff_fieldname: str) -> bool:
	"""True while the event is still further away than its Buzz Settings cutoff."""
	start_date = frappe.get_cached_value("Buzz Event", event_id, "start_date")
	if not start_date:
		return False

	cutoff_days = frappe.get_cached_doc("Buzz Settings").get(cutoff_fieldname, DEFAULT_CUTOFF_DAYS)
	return days_diff(start_date, today()) >= cutoff_days
