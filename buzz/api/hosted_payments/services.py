from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import frappe
from bwh_payments import api as payments
from frappe import _

from buzz.api.hosted_payments.exceptions import (
	ForeignSiteURL,
	NotAnIntegration,
	OrderNotFound,
	RefundExceedsBalance,
	RefundNotFound,
	UnsupportedCurrency,
)
from buzz.api.hosted_payments.schemas import HostedOrder, HostedRefund, OrderCustomer
from buzz.permissions import INTEGRATION_ROLE

RETURN_PATH = "/api/method/buzz.api.hosted_payments.return_to_site"
DEFAULT_PORTS = {"http": 80, "https": 443}


class HostedPayments:
	"""Payments the hub takes for a connected Pro site, as that team's integration user."""

	def __init__(self):
		filters = {"user": frappe.session.user, "team_role": INTEGRATION_ROLE, "enabled": 1}
		teams = frappe.get_all("Buzz Team Membership", filters=filters, pluck="team")
		if len(teams) != 1:
			NotAnIntegration.throw()
		self.team = teams[0]

	def payment_request(self, order_id: str) -> str:
		filters = {"name": order_id, "team": self.team}
		payment_request = frappe.db.get_value("Hosted Payment", filters, "payment_request")
		if not payment_request:
			OrderNotFound.throw()
		return payment_request

	def status(self, order_id: str) -> str:
		return frappe.db.get_value("Gateway Payment Request", self.payment_request(order_id), "status")

	def refund(self, order_id: str, amount: float) -> HostedRefund:
		payment_request = frappe.get_doc("Gateway Payment Request", self.payment_request(order_id))
		# Rounded as bwh_payments rounds it, so both sides agree on what is left to refund.
		amount = in_minor_units(amount, payment_request.currency_code)
		remaining = payment_request.get_remaining_refundable_amount()
		if amount > remaining:
			RefundExceedsBalance.throw(remaining=remaining)
		return hosted_refund(payments.refund(payment_request.name, amount, reference=order_id))

	def refund_status(self, order_id: str, refund_id: str) -> HostedRefund:
		filters = {"name": refund_id, "payment_request": self.payment_request(order_id)}
		if not frappe.db.exists("Gateway Refund", filters):
			RefundNotFound.throw()
		return hosted_refund(frappe.get_doc("Gateway Refund", refund_id))

	def currencies(self) -> list[str]:
		codes = frappe.db.get_single_value("Buzz Settings", "hosted_payment_currencies") or ""
		return [code.strip().upper() for code in codes.split(",") if code.strip()]

	def checkout_description(self, reference: str) -> str:
		team_name = frappe.db.get_value("Buzz Team", self.team, "team_name")
		return _("{0} via Buzz · {1}").format(team_name, reference)

	def validate_site_urls(self, *urls: str) -> None:
		"""The buyer and the ping go only to the team's own site, never where a caller points them."""
		connected_origin = site_origin(frappe.db.get_value("Buzz Team", self.team, "connected_site_url"))
		for url in urls:
			if not connected_origin or site_origin(url) != connected_origin:
				ForeignSiteURL.throw(url=url)

	def validate_currency(self, currency: str) -> None:
		if currency not in self.currencies():
			UnsupportedCurrency.throw(currency=currency)

	def create_order(
		self,
		amount: float,
		currency: str,
		reference: str,
		customer: OrderCustomer,
		return_url: str,
		webhook_url: str,
	) -> HostedOrder:
		currency = currency.upper()
		self.validate_site_urls(return_url, webhook_url)
		self.validate_currency(currency)
		payment = self.insert_payment(amount, currency, reference, customer, return_url, webhook_url)
		request = self.open_checkout(payment)
		return HostedOrder(order_id=payment.name, checkout_url=request.order_url)

	def insert_payment(
		self,
		amount: float,
		currency: str,
		reference: str,
		customer: OrderCustomer,
		return_url: str,
		webhook_url: str,
	):
		return frappe.get_doc(
			{
				"doctype": "Hosted Payment",
				"team": self.team,
				"amount": amount,
				"currency": currency,
				"reference": reference,
				"customer_email": customer.email,
				"customer_phone": customer.phone,
				"return_url": return_url,
				"webhook_url": webhook_url,
			}
		).insert(ignore_permissions=True)

	def open_checkout(self, payment):
		request = payments.create_payment(
			"Hosted Payment",
			payment.name,
			payment.amount,
			payment.currency,
			frappe.db.get_single_value("Buzz Settings", "hosted_payment_gateway"),
			redirect_to=f"{RETURN_PATH}?order_id={payment.name}",
			description=self.checkout_description(payment.reference),
			customer_email=payment.customer_email,
			customer_phone=payment.customer_phone,
		)
		payment.db_set("payment_request", request.name)
		return request


def return_location(order_id: str) -> str:
	return_url = frappe.db.get_value("Hosted Payment", order_id, "return_url")
	if not return_url:
		OrderNotFound.throw()
	parts = urlsplit(return_url)
	query = urlencode([*parse_qsl(parts.query), ("order_id", order_id)])
	return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def site_origin(url: str | None) -> tuple[str, str, int] | None:
	"""Scheme, host and port, with a missing port read as the scheme's default."""
	parts = urlsplit(url or "")
	if parts.scheme not in DEFAULT_PORTS or not parts.hostname:
		return None
	try:
		port = parts.port or DEFAULT_PORTS[parts.scheme]
	except ValueError:
		return None
	return parts.scheme, parts.hostname, port


def in_minor_units(amount: float, currency: str) -> float:
	return payments.from_minor_units(payments.to_minor_units(amount, currency), currency)


def hosted_refund(gateway_refund) -> HostedRefund:
	"""The hub's own Gateway Refund name is the id the connected site keeps."""
	return HostedRefund(
		refund_id=gateway_refund.name, status=gateway_refund.status, amount=gateway_refund.amount
	)
