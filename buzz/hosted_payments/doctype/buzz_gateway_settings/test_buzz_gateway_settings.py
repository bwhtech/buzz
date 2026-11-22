import frappe
from bwh_payments import testing as payment_testing
from frappe.tests import IntegrationTestCase
from frappe.utils import get_url

from buzz.hosted_payments.doctype.buzz_gateway_settings.buzz_gateway_settings import WEBHOOK_PATH
from buzz.install import create_buzz_payment_gateway
from buzz.patches.create_buzz_payment_gateway import execute as run_patch
from buzz.tests.base_test_cases import BUZZ_GATEWAY, BuzzGatewayTestCase


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
		self.assertEqual(session.redirect_url, get_url(f"/pay/{session.session_id}"))

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

	def paid_order(self) -> str:
		session = self.create_session()
		payment_testing.pay(self.hub_payment_request(session.session_id))
		return session.session_id

	def test_refund_is_made_on_the_hub(self):
		order_id = self.paid_order()
		result = self.gateway.refund_payment(order_id, 200, "INR")
		self.assertEqual((result.status, result.amount), ("Processed", 200))
		self.assertEqual(frappe.db.get_value("Hosted Payment", order_id, "refunded_amount"), 200)

	def test_pending_refund_status_comes_from_the_hub(self):
		order_id = self.paid_order()
		payment_testing.set_next_refund_status("Pending")
		pending = self.gateway.refund_payment(order_id, 200, "INR")
		self.assertEqual(self.gateway.get_refund_status(order_id, pending.refund_id).status, "Pending")
		payment_testing.send_refund_webhook(pending.refund_id, "Processed")
		self.assertEqual(self.gateway.get_refund_status(order_id, pending.refund_id).status, "Processed")

	def test_ping_names_the_order_to_sync(self):
		event = self.gateway.handle_webhook(b'{"order_id": "HP-1", "status": "Paid"}', {})
		self.assertEqual((event.session_id, event.status, event.sync_status), ("HP-1", "Pending", True))

	def test_malformed_ping_is_ignored(self):
		for payload in (b"not json", b"\xff", b"[]", b'{"status": "Paid"}', b'{"order_id": ["HP-1"]}'):
			with self.subTest(payload=payload):
				self.assertIsNone(self.gateway.handle_webhook(payload, {}))


class TestBuzzPaymentGatewayProfile(IntegrationTestCase):
	def profile(self) -> tuple | None:
		return frappe.db.get_value(
			"Payment Gateway Profile", BUZZ_GATEWAY, ["gateway_settings", "enabled"], as_dict=False
		)

	def test_install_and_patch_create_the_profile_disabled(self):
		for create in (create_buzz_payment_gateway, run_patch):
			with self.subTest(create=create.__module__):
				frappe.db.delete("Payment Gateway Profile", BUZZ_GATEWAY)
				create()
				self.assertEqual(self.profile(), ("Buzz Gateway Settings", 0))

	def test_patch_keeps_an_enabled_profile_enabled(self):
		frappe.db.set_value("Payment Gateway Profile", BUZZ_GATEWAY, "enabled", 1)
		run_patch()
		self.assertEqual(self.profile(), ("Buzz Gateway Settings", 1))
