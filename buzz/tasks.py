import frappe
from frappe.utils import today


def unpublish_ticket_types_after_last_date():
	frappe.db.set_value(
		"Event Ticket Type",
		{"is_published": True, "auto_unpublish_after": ("<", today())},
		"is_published",
		False,
	)
