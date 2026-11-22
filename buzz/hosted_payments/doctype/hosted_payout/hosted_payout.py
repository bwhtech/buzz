# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

SETTLEABLE_STATUSES = ("Paid", "Partially Refunded", "Refunded")


class HostedPayout(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.hosted_payments.doctype.hosted_payout_line.hosted_payout_line import HostedPayoutLine

		amended_from: DF.Link | None
		currency: DF.Link
		from_date: DF.Date
		lines: DF.Table[HostedPayoutLine]
		team: DF.Link
		to_date: DF.Date
		total_commission: DF.Currency
		total_gross: DF.Currency
		total_net: DF.Currency
		total_refunded: DF.Currency
		transfer_reference: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.set_totals()

	def before_submit(self):
		if not self.transfer_reference:
			frappe.throw(_("Set the Transfer Reference before you submit the payout."))
		self.validate_payments_unsettled()

	def validate_payments_unsettled(self) -> None:
		for line in self.lines:
			if frappe.db.get_value("Hosted Payment", line.hosted_payment, "payout", for_update=True):
				frappe.throw(
					_("Row {0}: Hosted Payment {1} is already paid out. Get payments again.").format(
						line.idx, line.hosted_payment
					)
				)

	def on_submit(self):
		self.set_payout_on_payments(self.name)

	def set_payout_on_payments(self, payout: str | None) -> None:
		names = [line.hosted_payment for line in self.lines]
		if names:
			frappe.db.set_value("Hosted Payment", {"name": ["in", names]}, "payout", payout)

	def set_totals(self) -> None:
		for field in ("gross", "refunded", "commission", "net"):
			self.set(f"total_{field}", sum(flt(line.get(field)) for line in self.lines))

	@frappe.whitelist(methods=["POST"])
	def get_payments(self) -> None:
		rates = PaymentRates()
		self.set("lines", [])
		for payment in self.unsettled_payments():
			self.append("lines", payment_line(payment, rates.rate(payment.payment_method)))

	def unsettled_payments(self) -> list[dict]:
		return frappe.get_all(
			"Hosted Payment",
			filters={
				"team": self.team,
				"currency": self.currency,
				"status": ["in", SETTLEABLE_STATUSES],
				"payout": ["is", "not set"],
				"creation": ["between", [self.from_date, self.to_date]],
			},
			fields=["name", "payment_method", "amount", "refunded_amount"],
			order_by="creation asc",
		)


class PaymentRates:
	"""Commission % per payment method, from Buzz Settings."""

	def __init__(self):
		settings = frappe.get_single("Buzz Settings")
		self.rates = {row.payment_method: row.rate for row in settings.hosted_payment_rates}
		self.fallback_rate = settings.hosted_payment_fallback_rate

	def rate(self, payment_method: str | None) -> float:
		return self.rates.get(payment_method, self.fallback_rate)


def payment_line(payment: dict, rate: float) -> dict:
	commission = flt(payment.amount * rate / 100, 2)
	return {
		"hosted_payment": payment.name,
		"payment_method": payment.payment_method,
		"rate": rate,
		"gross": payment.amount,
		"refunded": payment.refunded_amount,
		"commission": commission,
		"net": payment.amount - payment.refunded_amount - commission,
	}
