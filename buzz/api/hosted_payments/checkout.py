from typing import TYPE_CHECKING

import frappe
from bwh_payments import api as payments
from frappe.utils import get_url

from buzz.api.hosted_payments.exceptions import OrderNotFound
from buzz.api.hosted_payments.services import return_path

if TYPE_CHECKING:
	from bwh_payments.bwh_payments.doctype.gateway_payment_request.gateway_payment_request import (
		GatewayPaymentRequest,
	)

# Paid once, so the buyer goes back to the site; a refund does not reopen the checkout.
SETTLED_STATUSES = ("Paid", "Partially Refunded", "Refunded")
BUZZ_LOGO = "/assets/buzz/images/buzz-logo.svg"
# Espresso gray-900, the colour of the Buzz logo.
DIALOG_COLOR = "#171717"


class HostedCheckout:
	"""The buyer's side of one hub order: the pay page and its guest endpoints, keyed by the random order id."""

	def __init__(self, order_id: str):
		fields = ["name", "team", "payment_request"]
		self.order = frappe.db.get_value("Hosted Payment", order_id, fields, as_dict=True)
		if not (self.order and self.order.payment_request):
			OrderNotFound.throw()

	@property
	def payment_request(self) -> "GatewayPaymentRequest":
		return frappe.get_doc("Gateway Payment Request", self.order.payment_request)

	def status(self) -> str:
		"""Asked of the gateway while Pending, so a lost webhook does not keep the buyer waiting."""
		request = self.payment_request
		if request.status == "Pending":
			request.sync_status()
			# Frappe rolls back GET requests; the gateway's answer must be kept.
			frappe.local.flags.commit = True
		return request.status

	def confirm(self, payload: dict) -> str:
		return payments.confirm_embedded_payment(self.order.payment_request, payload)

	def page_config(self) -> dict:
		request = self.payment_request
		return {
			"order_id": self.order.name,
			"status": request.status,
			"checkout": self.dialog(request),
			"redirect_url": request.order_url if request.checkout == "Redirect" else None,
			"return_url": return_path(self.order.name),
			"team_name": frappe.db.get_value("Buzz Team", self.order.team, "team_name"),
		}

	def dialog(self, request: "GatewayPaymentRequest") -> dict | None:
		"""The gateway's script and options, with Buzz as the merchant the buyer sees."""
		if request.checkout != "Embedded":
			return None
		checkout = request.get_embedded_checkout()
		brand = {"name": "Buzz", "image": get_url(BUZZ_LOGO), "theme": {"color": DIALOG_COLOR}}
		return {"script_url": checkout.script_url, "options": checkout.options | brand}
