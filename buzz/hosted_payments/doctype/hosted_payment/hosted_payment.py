# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from buzz.hosted_payments.currency import round_to_currency
from buzz.hosted_payments.webhook_ping import enqueue_ping


class HostedPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		currency: DF.Link
		customer_email: DF.Data | None
		customer_phone: DF.Data | None
		deducted_refund_amount: DF.Currency
		next_ping_on: DF.Datetime | None
		paid_on: DF.Datetime | None
		payment_method: DF.Data | None
		ping_attempts: DF.Int
		ping_generation: DF.Int
		ping_status: DF.Literal["", "Pending", "Delivered", "Failed"]
		payment_request: DF.Link | None
		payout: DF.Link | None
		reference: DF.Data | None
		refunded_amount: DF.Currency
		return_url: DF.SmallText
		status: DF.Literal[
			"Pending", "Paid", "Not Paid", "Cancelled", "Expired", "Partially Refunded", "Refunded"
		]
		team: DF.Link
		webhook_url: DF.SmallText
	# end: auto-generated types

	def on_payment_authorized(self, status: str) -> None:
		payment_method = frappe.db.get_value(
			"Gateway Payment Request", self.payment_request, "payment_method"
		)
		# The status mirror on Gateway Payment Request sets the status.
		self.db_set({"payment_method": payment_method, "paid_on": now_datetime()})

	def on_refund_update(self, gateway_refund) -> None:
		self.db_set("refunded_amount", self.processed_refund_total())
		if gateway_refund.status != "Pending":
			enqueue_ping(self.name)

	def processed_refund_total(self) -> float:
		"""Locking reads under the request lock, since a plain read keeps the snapshot from before another
		refund settled."""
		frappe.db.get_value("Gateway Payment Request", self.payment_request, "name", for_update=True)
		amounts = frappe.db.get_values(
			"Gateway Refund",
			{"payment_request": self.payment_request, "status": "Processed"},
			"amount",
			for_update=True,
			pluck=True,
		)
		return round_to_currency(sum(flt(amount) for amount in amounts), self.currency)

	@frappe.whitelist(methods=["POST"])
	def ping_site_again(self) -> None:
		frappe.only_for("System Manager")
		enqueue_ping(self.name)
		frappe.msgprint(_("The connected site will be pinged again."), alert=True)
