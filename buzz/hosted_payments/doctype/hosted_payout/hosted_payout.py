# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from buzz.hosted_payments.currency import round_to_currency

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
		team_name: DF.Data | None
		to_date: DF.Date
		total_commission: DF.Currency
		total_gross: DF.Currency
		total_net: DF.Currency
		total_refunded: DF.Currency
		transfer_reference: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.validate_payments_are_unique()
		self.set_totals()

	def validate_payments_are_unique(self) -> None:
		seen = set()
		for line in self.lines:
			if line.hosted_payment in seen:
				frappe.throw(
					_("Row {0}: Hosted Payment {1} is already in this payout.").format(
						line.idx, line.hosted_payment
					)
				)
			seen.add(line.hosted_payment)

	def before_submit(self):
		if not self.transfer_reference:
			frappe.throw(_("Set the Transfer Reference before you submit the payout."))
		if not self.lines:
			frappe.throw(_("Get payments before you submit the payout."))
		self.validate_lines()

	def validate_lines(self) -> None:
		"""Each payment is this payout's team and currency. It settles once, and each refund of a settled
		payment is deducted once."""
		payments = lock_payments(self.payment_names())
		for line in self.lines:
			self.validate_line(line, payments[line.hosted_payment])

	def validate_line(self, line, payment: dict) -> None:
		if (payment.team, payment.currency) != (self.team, self.currency):
			frappe.throw(
				_("Row {0}: Hosted Payment {1} is not a {2} payment of team {3}.").format(
					line.idx, line.hosted_payment, self.currency, self.team
				)
			)
		if not line_is_unsettled(line, payment, self.currency):
			frappe.throw(
				_("Row {0}: Hosted Payment {1} has been paid out since. Get payments again.").format(
					line.idx, line.hosted_payment
				)
			)

	def payment_names(self) -> list[str]:
		return [line.hosted_payment for line in self.lines]

	def on_submit(self):
		self.update_payments(payout=self.name, direction=1)

	def before_cancel(self):
		"""Payout locks are only ever taken on the payout's own rows and its Hosted Payments, in that order,
		so a cancel and a submit wait for each other and never deadlock."""
		payments = lock_payments(self.payment_names())
		for line in self.lines:
			if not is_refund_line(line) and has_later_deductions(
				line, payments[line.hosted_payment], self.currency
			):
				frappe.throw(
					_("Payout {0} deducts refunds of Hosted Payment {1}. Cancel it first.").format(
						self.later_payout(line.hosted_payment), line.hosted_payment
					)
				)

	def later_payout(self, payment: str) -> str | None:
		return frappe.db.get_value(
			"Hosted Payout Line",
			{"hosted_payment": payment, "docstatus": 1, "parent": ["!=", self.name]},
			"parent",
		)

	def on_cancel(self):
		self.update_payments(payout=None, direction=-1)

	def update_payments(self, payout: str | None, direction: int) -> None:
		"""Settle or release each payment, and add or take back the refunds this payout deducts."""
		payments = lock_payments(self.payment_names())
		for line in self.lines:
			payment = payments[line.hosted_payment]
			deducted = flt(payment.deducted_refund_amount) + direction * flt(line.refunded)
			values = {"deducted_refund_amount": round_to_currency(deducted, self.currency)}
			if not is_refund_line(line):
				values["payout"] = payout
			frappe.db.set_value("Hosted Payment", payment.name, values)

	def set_totals(self) -> None:
		for field in ("gross", "refunded", "commission", "net"):
			total = sum(flt(line.get(field)) for line in self.lines)
			self.set(f"total_{field}", round_to_currency(total, self.currency))

	@frappe.whitelist(methods=["POST"])
	def get_payments(self) -> None:
		rates = PaymentRates()
		self.set("lines", [])
		for payment in self.unsettled_payments():
			self.append("lines", payment_line(payment, rates.rate(payment.payment_method), self.currency))
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
				"paid_on": ["between", [self.from_date, self.to_date]],
			},
			fields=["name", "payment_method", "amount", "refunded_amount"],
			order_by="paid_on asc",
		)

	def refunds_to_carry_forward(self):
		"""Settled payments refunded after their payout, with the refund not yet deducted."""
		payments = frappe.get_all(
			"Hosted Payment",
			filters=self.team_payment_filters() | {"payout": ["is", "set"], "refunded_amount": [">", 0]},
			fields=["name", "payment_method", "refunded_amount", "deducted_refund_amount"],
			order_by="creation asc",
		)
		for payment in payments:
			outstanding = outstanding_refund(payment, self.currency)
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


def lock_payments(names: list[str]) -> dict[str, dict]:
	"""Submit and cancel both lock the payments first, in name order, so each waits for the other."""
	if not names:
		return {}
	payments = frappe.db.get_values(
		"Hosted Payment",
		{"name": ["in", names]},
		["name", "team", "currency", "payout", "refunded_amount", "deducted_refund_amount"],
		as_dict=True,
		order_by="name asc",
		for_update=True,
	)
	return {payment.name: payment for payment in payments}


def outstanding_refund(payment: dict, currency: str) -> float:
	"""Refunded but not yet deducted on a submitted payout."""
	return round_to_currency(flt(payment.refunded_amount) - flt(payment.deducted_refund_amount), currency)


def has_later_deductions(line, payment: dict, currency: str) -> bool:
	"""Another submitted payout deducts refunds of the payment this line settles."""
	return round_to_currency(flt(payment.deducted_refund_amount) - flt(line.refunded), currency) > 0


def is_refund_line(line) -> bool:
	return line.line_type == "Refund"


def line_is_unsettled(line, payment: dict, currency: str) -> bool:
	if not is_refund_line(line):
		return not payment.payout
	return bool(payment.payout) and flt(line.refunded) <= outstanding_refund(payment, currency)


def payment_line(payment: dict, rate: float, currency: str) -> dict:
	commission = round_to_currency(payment.amount * rate / 100, currency)
	return {
		"hosted_payment": payment.name,
		"line_type": "Payment",
		"payment_method": payment.payment_method,
		"rate": rate,
		"gross": payment.amount,
		"refunded": payment.refunded_amount,
		"commission": commission,
		"net": round_to_currency(payment.amount - payment.refunded_amount - commission, currency),
	}


def refund_line(payment: dict, refunded: float) -> dict:
	"""Commission was kept at settlement, so only the refund is deducted."""
	return {
		"hosted_payment": payment.name,
		"line_type": "Refund",
		"payment_method": payment.payment_method,
		"rate": 0,
		"gross": 0,
		"refunded": refunded,
		"commission": 0,
		"net": -refunded,
	}
