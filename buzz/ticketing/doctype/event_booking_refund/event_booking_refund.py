# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.database.database import savepoint
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

		# Runs as Guest out of the webhook job; the signature already authenticated it.
		self.flags.ignore_permissions = True
		self.save()

		if self.cancellation_request:
			self.settle_cancellation_request()

	def settle_cancellation_request(self) -> None:
		"""Refunded tickets get cancelled, refused ones stay. Nobody needs to approve
		what the gateway already settled."""
		request = frappe.get_doc("Ticket Cancellation Request", self.cancellation_request)
		if request.docstatus != 0:
			return

		if self.status == "Failed":
			request.db_set("status", "Rejected")
			return

		# The refund is already recorded, so a cancellation that cannot go through
		# is undone whole and left in review rather than taking the refund with it.
		with savepoint(catch=Exception):
			request.status = "Accepted"
			request.flags.ignore_permissions = True
			request.submit()

		if frappe.db.get_value("Ticket Cancellation Request", request.name, "docstatus") == 0:
			frappe.log_error(f"Cancelling tickets after refund {self.name} failed")

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
