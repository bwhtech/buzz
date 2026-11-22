import frappe
from bwh_payments import testing as payment_testing
from frappe.utils import get_url

from buzz.api.hosted_payments import create_order, get_currencies, get_status, return_to_site
from buzz.api.hosted_payments.exceptions import ForeignSiteURL, OrderNotFound, UnsupportedCurrency
from buzz.api.listings.exceptions import NotAnIntegration
from buzz.tests.base_test_cases import HostedPaymentsTestCase
from buzz.tests.factories import BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory


class TestHostedPaymentsAPI(HostedPaymentsTestCase):
	def create_order(self, user: str | None = None, **overrides):
		with self.set_user(user or self.integration):
			return create_order(**self.order_values(**overrides))

	def test_create_order_opens_a_checkout_on_the_hub_gateway(self):
		order = self.create_order(amount=550)
		payment = frappe.get_doc("Hosted Payment", order.order_id)
		request = frappe.get_doc("Gateway Payment Request", payment.payment_request)
		self.assertEqual((payment.team, payment.amount, payment.status), (self.team, 550, "Pending"))
		self.assertEqual((request.gateway, request.ref_doctype), (self.hub_gateway, "Hosted Payment"))
		self.assertEqual(request.customer_email, "buyer@example.com")
		self.assertEqual(order.checkout_url, request.order_url)

	def test_only_a_team_integration_can_create_orders(self):
		manager = UserFactory.create_once("hosted-payments-manager@example.com").name
		BuzzTeamMembershipFactory.create(team=self.team, user=manager, team_role="Manager")
		with self.assertRaises(NotAnIntegration):
			self.create_order(user=manager)

	def test_return_url_must_be_on_the_connected_site(self):
		with self.assertRaises(ForeignSiteURL):
			self.create_order(return_url="https://attacker.example.com/steal")

	def test_webhook_url_must_be_on_the_connected_site(self):
		with self.assertRaises(ForeignSiteURL):
			self.create_order(webhook_url="https://attacker.example.com/hook")

	def test_rejected_order_leaves_no_payment(self):
		with self.assertRaises(ForeignSiteURL):
			self.create_order(return_url="javascript:alert(1)", reference="PRO-GPR-REJECTED")
		self.assertFalse(frappe.db.exists("Hosted Payment", {"reference": "PRO-GPR-REJECTED"}))

	def test_currencies_are_the_hub_list(self):
		self.enterContext(self.change_settings("Buzz Settings", hosted_payment_currencies="inr, USD"))
		with self.set_user(self.integration):
			self.assertEqual(get_currencies(), ["INR", "USD"])

	def test_create_order_rejects_other_currencies(self):
		with self.assertRaises(UnsupportedCurrency):
			self.create_order(currency="USD")

	def test_checkout_names_the_team_and_the_order(self):
		order = self.create_order(reference="PRO-GPR-7")
		request = frappe.db.get_value("Hosted Payment", order.order_id, "payment_request")
		self.assertEqual(
			frappe.db.get_value("Gateway Payment Request", request, "description"),
			"Pro Team via Buzz · PRO-GPR-7",
		)

	def pay(self, order_id: str, payment_method: str = "upi") -> None:
		request = frappe.db.get_value("Hosted Payment", order_id, "payment_request")
		payment_testing.pay(request, payment_method=payment_method)

	def test_new_order_is_pending(self):
		order = self.create_order()
		with self.set_user(self.integration):
			self.assertEqual(get_status(order.order_id), "Pending")

	def test_paying_the_checkout_marks_the_order_paid(self):
		order = self.create_order()
		self.pay(order.order_id)
		self.assertEqual(frappe.db.get_value("Hosted Payment", order.order_id, "status"), "Paid")
		with self.set_user(self.integration):
			self.assertEqual(get_status(order.order_id), "Paid")

	def test_paid_order_keeps_the_payment_method(self):
		order = self.create_order()
		self.pay(order.order_id, payment_method="card_credit")
		self.assertEqual(
			frappe.db.get_value("Hosted Payment", order.order_id, "payment_method"), "card_credit"
		)

	def test_another_team_cannot_read_an_order(self):
		order = self.create_order()
		other = UserFactory.create_once("hosted-payments-other-bot@example.com").name
		other_team = BuzzTeamFactory.create_owned_by(connected_site_url=get_url()).name
		BuzzTeamMembershipFactory.create(team=other_team, user=other, team_role="Integration")
		with self.set_user(other), self.assertRaises(OrderNotFound):
			get_status(order.order_id)

	def test_return_sends_the_buyer_back_to_the_site_with_the_order(self):
		frappe.db.set_value("Buzz Team", self.team, "connected_site_url", "https://pro.example.com")
		order = self.create_order(
			return_url="https://pro.example.com/return?request=PRO-GPR-1",
			webhook_url="https://pro.example.com/webhook",
		)
		with self.set_user("Guest"):
			return_to_site(order.order_id)
		self.assertEqual(frappe.local.response["type"], "redirect")
		self.assertEqual(
			frappe.local.response["location"],
			f"https://pro.example.com/return?request=PRO-GPR-1&order_id={order.order_id}",
		)

	def test_return_for_an_unknown_order_is_not_found(self):
		with self.set_user("Guest"), self.assertRaises(frappe.DoesNotExistError):
			return_to_site("no-such-order")
