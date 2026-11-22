import frappe
from bwh_payments import testing as payment_testing
from frappe.utils import get_url

from buzz.api.hosted_payments import (
	create_order,
	get_currencies,
	get_refund_status,
	get_status,
	refund,
	return_to_site,
)
from buzz.api.hosted_payments.exceptions import (
	ForeignSiteURL,
	OrderNotFound,
	RefundExceedsBalance,
	RefundNotFound,
	UnsupportedCurrency,
)
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

	def pay(self, order_id: str) -> None:
		payment_testing.pay(frappe.db.get_value("Hosted Payment", order_id, "payment_request"))

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


class TestHostedRefunds(HostedPaymentsTestCase):
	def setUp(self):
		super().setUp()
		with self.set_user(self.integration):
			self.order_id = create_order(**self.order_values(amount=550)).order_id
		payment_testing.pay(frappe.db.get_value("Hosted Payment", self.order_id, "payment_request"))

	def refund(self, amount: float, user: str | None = None):
		with self.set_user(user or self.integration):
			return refund(self.order_id, amount)

	def refunded_amount(self) -> float:
		return frappe.db.get_value("Hosted Payment", self.order_id, "refunded_amount")

	def test_full_refund(self):
		result = self.refund(550)
		self.assertEqual((result.status, result.amount), ("Processed", 550))
		self.assertEqual(self.refunded_amount(), 550)

	def test_two_partial_refunds(self):
		self.refund(200)
		second = self.refund(350)
		self.assertEqual((second.status, second.amount), ("Processed", 350))
		self.assertEqual(self.refunded_amount(), 550)

	def test_refund_over_the_balance_is_rejected(self):
		self.refund(500)
		with self.assertRaises(RefundExceedsBalance):
			self.refund(100)
		self.assertEqual(self.refunded_amount(), 500)

	def test_another_team_cannot_refund_an_order(self):
		other = UserFactory.create_once("hosted-refunds-other-bot@example.com").name
		other_team = BuzzTeamFactory.create_owned_by(connected_site_url=get_url()).name
		BuzzTeamMembershipFactory.create(team=other_team, user=other, team_role="Integration")
		with self.assertRaises(OrderNotFound):
			self.refund(100, user=other)
		self.assertEqual(self.refunded_amount(), 0)

	def refund_status(self, refund_id: str, user: str | None = None):
		with self.set_user(user or self.integration):
			return get_refund_status(self.order_id, refund_id)

	def test_pending_refund_counts_once_the_gateway_settles_it(self):
		payment_testing.set_next_refund_status("Pending")
		pending = self.refund(200)
		self.assertEqual((pending.status, self.refunded_amount()), ("Pending", 0))
		payment_testing.send_refund_webhook(pending.refund_id, "Processed")
		settled = self.refund_status(pending.refund_id)
		self.assertEqual(
			(settled.refund_id, settled.status, settled.amount), (pending.refund_id, "Processed", 200)
		)
		self.assertEqual(self.refunded_amount(), 200)

	def test_refund_of_another_order_is_not_found(self):
		other_order = self.create_other_order()
		other_refund = self.refund(100)
		with self.set_user(self.integration), self.assertRaises(RefundNotFound):
			get_refund_status(other_order, other_refund.refund_id)

	def create_other_order(self) -> str:
		with self.set_user(self.integration):
			return create_order(**self.order_values()).order_id
