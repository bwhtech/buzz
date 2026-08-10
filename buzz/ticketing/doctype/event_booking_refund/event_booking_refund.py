# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

# A refund that the gateway has not rejected still holds money and tickets.
COMMITTED_STATUSES = ("Initiated", "Processed")


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
		"""Record what the gateway settled, and stop cancelling tickets it refused."""
		self.amount = flt(amount)
		self.status = "Failed" if gateway_status == "failed" else "Processed"

		if self.status == "Failed" and self.cancellation_request:
			frappe.db.set_value(
				"Ticket Cancellation Request", self.cancellation_request, "status", "Rejected"
			)

		# The gateway webhook is an allow_guest endpoint, so the job carrying this
		# call runs as Guest. Authentication already happened on the signature.
		self.flags.ignore_permissions = True
		self.save()

	def on_update(self):
		frappe.get_doc("Event Booking", self.booking).set_refund_status()


def get_committed_refunds(booking: str) -> list[frappe._dict]:
	"""Refunds holding money against a booking — everything the gateway has not refused."""
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
