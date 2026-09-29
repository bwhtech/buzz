# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.database.database import savepoint
from frappe.model.document import Document
from frappe.utils import flt

# A refund that the gateway has not rejected still holds money and tickets.
COMMITTED_STATUSES = ("Initiated", "Processed")

# What the gateway settled on. Anything else is still in flight.
FINAL_STATUSES = ("Processed", "Failed")

GATEWAY_STATUSES = {"processed": "Processed", "failed": "Failed"}


class EventBookingRefund(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.ticketing.doctype.event_booking_refund_ticket.event_booking_refund_ticket import (
			EventBookingRefundTicket,
		)

		amount: DF.Currency
		booking: DF.Link
		cancellation_request: DF.Link | None
		currency: DF.Link | None
		payment: DF.Link | None
		refund_id: DF.Data | None
		status: DF.Literal["Initiated", "Processed", "Failed"]
		tickets: DF.TableMultiSelect[EventBookingRefundTicket]
	# end: auto-generated types

	def apply_gateway_status(self, gateway_status: str, amount: float) -> None:
		"""Record what the gateway settled on this refund."""
		# A settled refund does not un-settle: a sync can read a stale `pending`,
		# or arrive behind the webhook that already recorded the outcome.
		if self.status in FINAL_STATUSES:
			return

		self.amount = flt(amount)
		self.status = GATEWAY_STATUSES.get(gateway_status, "Initiated")

		# Runs as Guest out of the webhook job; the signature already authenticated it.
		self.flags.ignore_permissions = True
		self.save()

		if self.status == "Processed" and self.tickets and not self.cancellation_request:
			self.cancel_refunded_tickets()

	def cancel_refunded_tickets(self) -> None:
		"""Cancel the tickets this refund paid back for."""
		# Cancelled here and not when the refund went out: a refund can still
		# fail, and a ticket cancelled against one leaves the customer with
		# neither money nor a seat. What the gateway settled needs no approval.
		request = frappe.get_doc(
			{
				"doctype": "Ticket Cancellation Request",
				"booking": self.booking,
				"status": "In Review",
				"tickets": [{"ticket": row.ticket} for row in self.tickets],
			}
		)
		request.flags.ignore_permissions = True
		request.insert()
		self.db_set("cancellation_request", request.name)

		# The refund is already recorded, so a cancellation that cannot go through
		# is undone whole and left in review rather than taking the refund with it.
		with savepoint(catch=Exception):
			request.status = "Accepted"
			request.submit()

		if frappe.db.get_value("Ticket Cancellation Request", request.name, "docstatus") == 0:
			frappe.log_error(f"Cancelling tickets after refund {self.name} failed")

	def on_update(self):
		frappe.get_doc("Event Booking", self.booking).set_refund_status()


def record_gateway_refund(
	booking: str, payment: str | None, refund_id: str, status: str, amount: float
) -> bool:
	"""Create or update the refund `refund_id` names. True when it was new.

	Used for refunds the gateway reports, from the webhook or a sync — never for
	one raised from the Desk, which records the tickets an operator picked.
	"""
	# The webhook job and a Desk sync can both be recording refunds on this
	# booking. Serialising them here is what lets the reads below see every
	# refund that came before, rather than a picture from an instant ago.
	frappe.db.get_value("Event Booking", booking, "name", for_update=True)

	existing = frappe.db.exists("Event Booking Refund", {"refund_id": refund_id})
	if existing:
		refund = frappe.get_doc("Event Booking Refund", existing)
	else:
		refund = frappe.get_doc(
			{
				"doctype": "Event Booking Refund",
				"booking": booking,
				"payment": payment,
				"refund_id": refund_id,
				"currency": frappe.db.get_value("Event Booking", booking, "currency"),
				"tickets": [{"ticket": ticket} for ticket in tickets_a_refund_covers(booking, amount)],
			}
		).insert(ignore_permissions=True)

	refund.apply_gateway_status(gateway_status=status, amount=amount)

	return not existing


def tickets_a_refund_covers(booking: str, amount: float) -> list[str]:
	"""The tickets a refund raised outside Buzz pays back for: what is left, or nothing."""
	# Read before the refund is recorded: `remaining` is already net of every
	# refund the booking holds, so a refund counts itself out once it is stored.
	doc = frappe.get_doc("Event Booking", booking)
	summary = doc.get_refund_summary()
	precision = doc.precision("total_amount")

	if flt(amount, precision) < flt(summary["remaining"], precision):
		return []

	return [ticket["ticket"] for ticket in summary["tickets"]]


def get_committed_refunds(booking: str) -> list[frappe._dict]:
	"""Get the refunds still holding money against a booking."""
	return frappe.get_all(
		"Event Booking Refund",
		filters={"booking": booking, "status": ("in", COMMITTED_STATUSES)},
		fields=["name", "amount"],
	)


def get_committed_tickets(booking: str) -> set[str]:
	return set(
		frappe.get_all(
			"Event Booking Refund Ticket",
			filters={
				"parenttype": "Event Booking Refund",
				"parent": ("in", [refund.name for refund in get_committed_refunds(booking)] or [""]),
			},
			pluck="ticket",
		)
	)
