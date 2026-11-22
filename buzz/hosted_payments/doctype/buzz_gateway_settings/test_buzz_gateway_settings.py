import frappe
from bwh_payments import testing as payment_testing
from frappe.utils import get_url

from buzz.hosted_payments.doctype.buzz_gateway_settings.buzz_gateway_settings import WEBHOOK_PATH
from buzz.tests.base_test_cases import BuzzGatewayTestCase


class TestBuzzGatewaySettings(BuzzGatewayTestCase):
	@property
	def gateway(self):
		return frappe.get_single("Buzz Gateway Settings")

	def create_session(self):
		return self.gateway.create_session(
			550,
			"INR",
			reference="PRO-GPR-7",
			customer={"email": "buyer@example.com", "phone": "+91-9999999999"},
			return_url=get_url("/api/method/pro.return?request=PRO-GPR-7"),
		)

	def test_session_is_a_hub_order(self):
		session = self.create_session()
		payment = frappe.get_doc("Hosted Payment", session.session_id)
		self.assertEqual((payment.reference, payment.amount, payment.team), ("PRO-GPR-7", 550, self.team))
		self.assertEqual(payment.webhook_url, get_url(WEBHOOK_PATH))
		request_url = frappe.db.get_value("Gateway Payment Request", payment.payment_request, "order_url")
		self.assertEqual(session.redirect_url, request_url)

	def test_payment_status_comes_from_the_hub(self):
		session = self.create_session()
		self.assertEqual(self.gateway.get_payment_status(session.session_id), "Pending")
		payment_testing.pay(self.hub_payment_request(session.session_id))
		self.assertEqual(self.gateway.get_payment_status(session.session_id), "Paid")

	def test_currencies_come_from_the_hub_and_are_cached(self):
		self.enterContext(self.change_settings("Buzz Settings", hosted_payment_currencies="INR, USD"))
		self.assertEqual(self.gateway.supported_currencies(), ("INR", "USD"))
		self.enterContext(self.change_settings("Buzz Settings", hosted_payment_currencies="INR"))
		self.assertEqual(self.gateway.supported_currencies(), ("INR", "USD"))
