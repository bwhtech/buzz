import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.hosted_payments import services
from buzz.api.hosted_payments.checkout import HostedCheckout
from buzz.api.hosted_payments.schemas import HostedOrder, HostedRefund, OrderCustomer
from buzz.api.hosted_payments.services import HostedPayments


@frappe.whitelist(methods=["POST"])
def create_order(
	amount: float, currency: str, reference: str, customer: OrderCustomer, return_url: str, webhook_url: str
) -> HostedOrder:
	return HostedPayments().create_order(amount, currency, reference, customer, return_url, webhook_url)


@frappe.whitelist()
def get_status(order_id: str) -> str:
	"""The order's Gateway Payment Request status."""
	return HostedPayments().status(order_id)


@frappe.whitelist(methods=["POST"])
def refund(order_id: str, amount: float) -> HostedRefund:
	return HostedPayments().refund(order_id, amount)


@frappe.whitelist(methods=["POST"])
def get_refund_status(order_id: str, refund_id: str) -> HostedRefund:
	return HostedPayments().refund_status(order_id, refund_id)


@frappe.whitelist()
def get_currencies() -> list[str]:
	return HostedPayments().currencies()


# nosemgrep: guest-whitelisted-method  # the hub checkout sends the buyer's browser here; it only reads
@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=60, seconds=60, ip_based=True)
def return_to_site(order_id: str) -> None:
	"""Send the buyer from the hub checkout back to the connected site, which confirms the payment."""
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = services.return_location(order_id)


# nosemgrep: guest-whitelisted-method  # the buyer's pay page polls it; it returns the status only
@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=60, seconds=60, ip_based=True)
def get_checkout_status(order_id: str) -> str:
	return HostedCheckout(order_id).status()


# nosemgrep: guest-whitelisted-method  # the gateway dialog's result, checked against the gateway's signature
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60, ip_based=True)
def confirm_checkout(order_id: str, payload: dict) -> str:
	"""Confirm what the gateway's dialog handed the pay page, and return the order's status."""
	return HostedCheckout(order_id).confirm(payload)
