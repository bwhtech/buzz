from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import frappe
from bwh_payments import api as payments
from frappe import _

from buzz.api.hosted_payments.exceptions import ForeignSiteURL, OrderNotFound, UnsupportedCurrency
from buzz.api.hosted_payments.schemas import HostedOrder
from buzz.api.listings.exceptions import NotAnIntegration
from buzz.permissions import INTEGRATION_ROLE

RETURN_PATH = "/api/method/buzz.api.hosted_payments.return_to_site"


class HostedPayments:
	"""Payments the hub takes for a connected Pro site, as that team's integration user."""

	def __init__(self):
		filters = {"user": frappe.session.user, "team_role": INTEGRATION_ROLE, "enabled": 1}
		teams = frappe.get_all("Buzz Team Membership", filters=filters, pluck="team")
		if len(teams) != 1:
			NotAnIntegration.throw()
		self.team = teams[0]

	def status(self, order_id: str) -> str:
		filters = {"name": order_id, "team": self.team}
		payment_request = frappe.db.get_value("Hosted Payment", filters, "payment_request")
		if not payment_request:
			OrderNotFound.throw()
		return frappe.db.get_value("Gateway Payment Request", payment_request, "status")

	def currencies(self) -> list[str]:
		codes = frappe.db.get_single_value("Buzz Settings", "hosted_payment_currencies") or ""
		return [code.strip().upper() for code in codes.split(",") if code.strip()]

	def checkout_description(self, reference: str) -> str:
		team_name = frappe.db.get_value("Buzz Team", self.team, "team_name")
		return _("{0} via Buzz · {1}").format(team_name, reference)

	def validate_site_urls(self, *urls: str) -> None:
		"""The buyer and the ping go only to the team's own site, never where a caller points them."""
		connected_host = site_host(frappe.db.get_value("Buzz Team", self.team, "connected_site_url"))
		for url in urls:
			if not connected_host or site_host(url) != connected_host:
				ForeignSiteURL.throw(url=url)

	def create_order(
		self, amount: float, currency: str, reference: str, customer: dict, return_url: str, webhook_url: str
	) -> HostedOrder:
		self.validate_site_urls(return_url, webhook_url)
		if currency not in self.currencies():
			UnsupportedCurrency.throw(currency=currency)
		gateway = frappe.db.get_single_value("Buzz Settings", "hosted_payment_gateway")
		payment = frappe.get_doc(
			{
				"doctype": "Hosted Payment",
				"team": self.team,
				"amount": amount,
				"currency": currency,
				"reference": reference,
				"customer_email": customer.get("email"),
				"customer_phone": customer.get("phone"),
				"return_url": return_url,
				"webhook_url": webhook_url,
			}
		).insert(ignore_permissions=True)
		request = payments.create_payment(
			"Hosted Payment",
			payment.name,
			amount,
			currency,
			gateway,
			redirect_to=f"{RETURN_PATH}?order_id={payment.name}",
			description=self.checkout_description(reference),
			customer_email=payment.customer_email,
			customer_phone=payment.customer_phone,
		)
		payment.db_set("payment_request", request.name)
		return HostedOrder(order_id=payment.name, checkout_url=request.order_url)


def return_location(order_id: str) -> str:
	return_url = frappe.db.get_value("Hosted Payment", order_id, "return_url")
	if not return_url:
		raise frappe.DoesNotExistError(_("Payment not found"))
	parts = urlsplit(return_url)
	query = urlencode([*parse_qsl(parts.query), ("order_id", order_id)])
	return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def site_host(url: str | None) -> str | None:
	parts = urlsplit(url or "")
	return parts.hostname if parts.scheme in ("http", "https") else None
