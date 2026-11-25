import json
import re
from unittest.mock import patch

import frappe
from bwh_payments import testing as payment_testing
from bwh_payments.bwh_payments.doctype.razorpay_gateway_settings.razorpay_gateway_settings import (
	RazorpayGatewaySettings,
)
from bwh_payments.services.razorpay.stub import (  # nosemgrep: frappe-monkey-patching-not-allowed
	StubRazorpayClient,
)
from frappe.utils import get_url, set_request
from frappe.website.serve import get_response

from buzz.api.hosted_payments import confirm_checkout, create_order, get_checkout_status
from buzz.api.hosted_payments.exceptions import OrderNotFound
from buzz.tests.base_test_cases import HostedPaymentsTestCase

RETURN_PATH = "/api/method/buzz.api.hosted_payments.return_to_site"


class TestHostedCheckout(HostedPaymentsTestCase):
	def setUp(self):
		super().setUp()
		# CI never runs bench build, so there is no assets.json for bundled_asset to read.
		self.enterContext(patch("frappe.utils.get_assets_json", return_value={}))
		with self.set_user(self.integration):
			self.order = create_order(**self.order_values(amount=550))
		self.order_id = self.order.order_id

	def hub_request(self, order_id: str | None = None):
		name = frappe.db.get_value("Hosted Payment", order_id or self.order_id, "payment_request")
		return frappe.get_doc("Gateway Payment Request", name)

	def visit(self, order_id: str):
		# A real server starts each request afresh; get_url() would read this request's host.
		self.addCleanup(setattr, frappe.local, "request", getattr(frappe.local, "request", None))
		self.addCleanup(setattr, frappe.flags, "redirect_location", None)
		with self.set_user("Guest"):
			set_request(method="GET", path=f"/pay/{order_id}")
			return get_response(f"/pay/{order_id}")

	def page_config(self, response) -> dict:
		html = response.get_data(as_text=True)
		found = re.search(r'<script type="application/json" id="checkout-config">(.*?)</script>', html, re.S)
		return json.loads(found.group(1))

	def as_guest(self, endpoint, *arguments):
		with self.set_user("Guest"):
			return endpoint(*arguments)

	def test_order_sends_the_buyer_to_the_pay_page(self):
		self.assertEqual(self.order.checkout_url, get_url(f"/pay/{self.order_id}"))
		request = self.hub_request()
		self.assertEqual((request.checkout, request.redirect_to), ("Embedded", f"/pay/{self.order_id}"))

	def test_pay_page_opens_the_razorpay_dialog_for_the_order(self):
		response = self.visit(self.order_id)
		self.assertEqual(response.status_code, 200)
		self.assertIn("Processing your payment securely", response.get_data(as_text=True))
		config = self.page_config(response)
		options = config["checkout"]["options"]
		self.assertEqual(config["checkout"]["script_url"], "https://checkout.razorpay.com/v1/checkout.js")
		self.assertEqual((options["order_id"], options["amount"]), (self.hub_request().order_ref, 55000))
		self.assertEqual(options["description"], "Pro Team via Buzz · PRO-GPR-1")
		self.assertEqual(config["return_url"], f"{RETURN_PATH}?order_id={self.order_id}")
		self.assertEqual(config["team_name"], "Pro Team")

	def test_pay_page_for_an_unknown_order_is_not_found(self):
		self.assertEqual(self.visit("no-such-order").status_code, 404)

	def test_pay_page_for_a_paid_order_sends_the_buyer_back_at_once(self):
		payment_testing.pay(self.hub_request().name)
		response = self.visit(self.order_id)
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.headers["Location"], f"{RETURN_PATH}?order_id={self.order_id}")

	def test_pay_page_redirects_to_a_gateway_without_a_dialog(self):
		with patch.object(RazorpayGatewaySettings, "supports_embedded_checkout", False):
			with self.set_user(self.integration):
				order_id = create_order(**self.order_values()).order_id
		config = self.page_config(self.visit(order_id))
		self.assertIsNone(config["checkout"])
		self.assertEqual(config["redirect_url"], self.hub_request(order_id).order_url)

	def test_checkout_status_is_read_by_the_order_id(self):
		self.assertEqual(self.as_guest(get_checkout_status, self.order_id), "Pending")
		payment_testing.pay(self.hub_request().name)
		self.assertEqual(self.as_guest(get_checkout_status, self.order_id), "Paid")

	def test_checkout_status_asks_the_gateway_while_pending(self):
		StubRazorpayClient.pay(self.hub_request().order_ref)
		self.assertEqual(self.as_guest(get_checkout_status, self.order_id), "Paid")
		self.assertEqual(frappe.db.get_value("Hosted Payment", self.order_id, "status"), "Paid")

	def test_checkout_status_of_an_unknown_order_is_not_found(self):
		with self.assertRaises(OrderNotFound):
			self.as_guest(get_checkout_status, "no-such-order")

	def test_dialog_payment_marks_the_order_paid(self):
		result = payment_testing.complete_embedded_checkout(self.hub_request().name)
		self.assertEqual(self.as_guest(confirm_checkout, self.order_id, result), "Paid")
		payment = frappe.get_doc("Hosted Payment", self.order_id)
		self.assertEqual(payment.status, "Paid")
		self.assertTrue(payment.paid_on)

	def test_forged_dialog_payment_is_rejected(self):
		result = payment_testing.complete_embedded_checkout(self.hub_request().name)
		with self.assertRaises(frappe.ValidationError):
			self.as_guest(confirm_checkout, self.order_id, result | {"razorpay_signature": "0" * 64})
		self.assertEqual(frappe.db.get_value("Hosted Payment", self.order_id, "status"), "Pending")
