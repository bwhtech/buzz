import frappe
from frappe.utils import add_to_date, now, today

from buzz.payments import sync_gateway_payment


def unpublish_ticket_types_after_last_date():
	frappe.db.set_value(
		"Event Ticket Type",
		{"is_published": True, "auto_unpublish_after": ("<", today())},
		"is_published",
		False,
	)


def sync_pending_online_payments():
	"""Confirm bookings the gateway took money for but the browser never reported.

	The buyer's browser is what tells Buzz a payment went through, so a closed tab leaves
	the booking in draft and its tickets unissued.
	"""
	for booking in get_bookings_awaiting_payment():
		# ponytail: a savepoint per booking, so one gateway failure cannot undo the rest.
		frappe.db.savepoint("sync_payment")
		try:
			sync_gateway_payment("Event Booking", booking)
		except Exception:
			frappe.db.rollback(save_point="sync_payment")
			frappe.log_error(
				title="Payment sync failed", reference_doctype="Event Booking", reference_name=booking
			)


def get_bookings_awaiting_payment() -> list[str]:
	"""Bookings still waiting on an online payment, old enough that the browser is not coming back."""
	# ponytail: no gateway filter, a booking abandoned before checkout costs one cheap miss.
	# 15 minutes leaves a checkout still in flight alone; 3 days is as far back as one is chased.
	return frappe.get_all(
		"Event Booking",
		filters={
			"docstatus": 0,
			"payment_status": "Unpaid",
			"creation": [
				"between",
				(add_to_date(now(), days=-3), add_to_date(now(), minutes=-15)),
			],
		},
		pluck="name",
	)
