# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
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
		if not self.lines:
			frappe.throw(_("Get payments before you submit the payout."))
		self.validate_lines_unsettled()

	def validate_lines_unsettled(self) -> None:
		"""Each payment settles once, and each refund of a settled payment is deducted once."""
		names = [line.hosted_payment for line in self.lines]
		payments = {
			payment.name: payment
			for payment in frappe.db.get_values(
				"Hosted Payment",
				{"name": ["in", names]},
				["name", "payout", "refunded_amount"],
				as_dict=True,
				for_update=True,
			)
		}
		deducted = deducted_refunds(names)
		for line in self.lines:
			if not line_is_unsettled(line, payments[line.hosted_payment], deducted):
				frappe.throw(
					_("Row {0}: Hosted Payment {1} has been paid out since. Get payments again.").format(
						line.idx, line.hosted_payment
					)
				)

	def on_submit(self):
		names = self.settled_payments()
		if names:
			frappe.db.set_value("Hosted Payment", {"name": ["in", names]}, "payout", self.name)

	def settled_payments(self) -> list[str]:
		return [line.hosted_payment for line in self.lines if not is_refund_line(line)]

	def before_cancel(self):
		later_payout = frappe.db.get_value(
			"Hosted Payout Line",
			{"hosted_payment": ["in", self.settled_payments()], "docstatus": 1, "parent": ["!=", self.name]},
			"parent",
		)
		if later_payout:
			frappe.throw(
				_("Payout {0} deducts refunds of these payments. Cancel it first.").format(later_payout)
			)

	def on_cancel(self):
		frappe.db.set_value("Hosted Payment", {"payout": self.name}, "payout", None)

	def set_totals(self) -> None:
		for field in ("gross", "refunded", "commission", "net"):
			self.set(f"total_{field}", sum(flt(line.get(field)) for line in self.lines))

	@frappe.whitelist(methods=["POST"])
	def get_payments(self) -> None:
		rates = PaymentRates()
		self.set("lines", [])
		for payment in self.unsettled_payments():
			self.append("lines", payment_line(payment, rates.rate(payment.payment_method)))
		for payment, refunded in self.refunds_to_carry_forward():
			self.append("lines", refund_line(payment, refunded))
		self.set_totals()

	def team_payment_filters(self) -> dict:
		return {"team": self.team, "currency": self.currency}

	def unsettled_payments(self) -> list[dict]:
		return frappe.get_all(
			"Hosted Payment",
			filters=self.team_payment_filters()
			| {
				"status": ["in", SETTLEABLE_STATUSES],
				"payout": ["is", "not set"],
				"creation": ["between", [self.from_date, self.to_date]],
			},
			fields=["name", "payment_method", "amount", "refunded_amount"],
			order_by="creation asc",
		)

	def refunds_to_carry_forward(self):
		"""Settled payments refunded after their payout, with the refund not yet deducted."""
		payments = frappe.get_all(
			"Hosted Payment",
			filters=self.team_payment_filters() | {"payout": ["is", "set"], "refunded_amount": [">", 0]},
			fields=["name", "payment_method", "refunded_amount"],
			order_by="creation asc",
		)
		deducted = deducted_refunds([payment.name for payment in payments])
		for payment in payments:
			outstanding = flt(payment.refunded_amount - deducted.get(payment.name, 0), 2)
			if outstanding > 0:
				yield payment, outstanding


class PaymentRates:
	"""Commission % per payment method, from Buzz Settings."""

	def __init__(self):
		settings = frappe.get_single("Buzz Settings")
		self.rates = {row.payment_method: row.rate for row in settings.hosted_payment_rates}
		self.fallback_rate = settings.hosted_payment_fallback_rate

	def rate(self, payment_method: str | None) -> float:
		return self.rates.get(payment_method, self.fallback_rate)


def deducted_refunds(payments: list[str]) -> dict[str, float]:
	"""Refunded amounts already counted on submitted payouts, per payment."""
	if not payments:
		return {}
	line = frappe.qb.DocType("Hosted Payout Line")
	query = (
		frappe.qb.from_(line)
		.select(line.hosted_payment, Sum(line.refunded))
		.where((line.docstatus == 1) & line.hosted_payment.isin(payments))
		.groupby(line.hosted_payment)
	)
	return dict(query.run())


def is_refund_line(line) -> bool:
	return not flt(line.gross)


def line_is_unsettled(line, payment: dict, deducted: dict[str, float]) -> bool:
	if not is_refund_line(line):
		return not payment.payout
	already_deducted = flt(deducted.get(payment.name))
	return bool(payment.payout) and already_deducted + flt(line.refunded) <= flt(payment.refunded_amount)


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


def refund_line(payment: dict, refunded: float) -> dict:
	"""Commission was kept at settlement, so only the refund is deducted."""
	return {
		"hosted_payment": payment.name,
		"payment_method": payment.payment_method,
		"rate": 0,
		"gross": 0,
		"refunded": refunded,
		"commission": 0,
		"net": -refunded,
	}
