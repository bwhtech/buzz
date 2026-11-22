from unittest.mock import patch

import frappe
import requests
from bwh_payments import testing as payment_testing
from bwh_payments.bwh_payments.doctype.gateway_refund.gateway_refund import GatewayRefund
from bwh_payments.bwh_payments.doctype.razorpay_gateway_settings.razorpay_gateway_settings import (
	RazorpayGatewaySettings,
)
from bwh_payments.services.razorpay.stub import (  # nosemgrep: frappe-monkey-patching-not-allowed
	StubRazorpayClient,
)
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
	InvalidCustomer,
	NotAnIntegration,
	OrderNotFound,
	RefundExceedsBalance,
	RefundNotFound,
	UnsupportedCurrency,
)
from buzz.hosted_payments.webhook_ping import ping_site
from buzz.tests.base_test_cases import HostedPaymentsTestCase
from buzz.tests.factories import BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory


def pings_after(change_status) -> list[dict]:
	"""Capture the pings and run every other job, such as bwh_payments applying a webhook."""
	pings, enqueue = [], frappe.enqueue

	def capture(method, **kwargs):
		if method is not ping_site:
			return enqueue(method, **kwargs)
		pings.append(kwargs)

	with patch("frappe.enqueue", side_effect=capture):
		change_status()
	return pings


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

	def connect_site(self, url: str) -> None:
		connected = frappe.db.get_value("Buzz Team", self.team, "connected_site_url")
		self.addCleanup(frappe.db.set_value, "Buzz Team", self.team, "connected_site_url", connected)
		frappe.db.set_value("Buzz Team", self.team, "connected_site_url", url)

	def test_return_url_on_another_port_is_rejected(self):
		self.connect_site("https://pro.example.com")
		with self.assertRaises(ForeignSiteURL):
			self.create_order(
				return_url="https://pro.example.com:8443/return", webhook_url="https://pro.example.com/hook"
			)

	def test_return_url_on_another_scheme_is_rejected(self):
		self.connect_site("https://pro.example.com")
		with self.assertRaises(ForeignSiteURL):
			self.create_order(
				return_url="http://pro.example.com/return", webhook_url="https://pro.example.com/hook"
			)

	def test_default_port_matches_a_site_url_without_one(self):
		self.connect_site("https://pro.example.com")
		order = self.create_order(
			return_url="https://pro.example.com:443/return", webhook_url="https://pro.example.com/hook"
		)
		self.assertTrue(frappe.db.exists("Hosted Payment", order.order_id))

	def test_customer_with_an_invalid_email_is_rejected(self):
		with self.assertRaises(InvalidCustomer):
			self.create_order(customer={"email": "not-an-email"}, reference="PRO-GPR-BAD-EMAIL")
		self.assertFalse(frappe.db.exists("Hosted Payment", {"reference": "PRO-GPR-BAD-EMAIL"}))

	def test_customer_with_an_invalid_phone_is_rejected(self):
		with self.assertRaises(InvalidCustomer):
			self.create_order(customer={"email": "buyer@example.com", "phone": "call me"})

	def test_customer_without_contact_details_is_accepted(self):
		order = self.create_order(customer={"email": "", "phone": ""})
		payment = frappe.get_doc("Hosted Payment", order.order_id)
		self.assertEqual((payment.customer_email, payment.customer_phone), (None, None))

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

	def test_currency_is_matched_in_any_case_and_stored_upper_case(self):
		order = self.create_order(currency="inr")
		self.assertEqual(frappe.db.get_value("Hosted Payment", order.order_id, "currency"), "INR")

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
		self.connect_site("https://pro.example.com")
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
		with self.set_user("Guest"), self.assertRaises(OrderNotFound):
			return_to_site("no-such-order")

	def expire(self, order_id: str) -> None:
		request = frappe.get_doc(
			"Gateway Payment Request", frappe.db.get_value("Hosted Payment", order_id, "payment_request")
		)
		StubRazorpayClient.set_status(request.order_ref, "expired")
		request.sync_status()

	def test_payment_pings_the_stored_webhook_url(self):
		order = self.create_order(webhook_url=get_url("/api/method/pro.webhook?gateway=Buzz&site=1"))
		pings = pings_after(lambda: self.pay(order.order_id))
		self.assertEqual(len(pings), 1)
		self.assertEqual(pings[0]["webhook_url"], get_url("/api/method/pro.webhook?gateway=Buzz&site=1"))
		self.assertEqual((pings[0]["order_id"], pings[0]["enqueue_after_commit"]), (order.order_id, True))

	def test_expiry_is_mirrored_and_pinged(self):
		# A Razorpay order never expires, so this order takes the payment link a redirect gateway opens.
		with patch.object(RazorpayGatewaySettings, "supports_embedded_checkout", False):
			order = self.create_order()
		pings = pings_after(lambda: self.expire(order.order_id))
		self.assertEqual([ping["order_id"] for ping in pings], [order.order_id])
		self.assertEqual(frappe.db.get_value("Hosted Payment", order.order_id, "status"), "Expired")

	def test_new_order_does_not_ping(self):
		self.assertEqual(pings_after(self.create_order), [])

	def test_ping_posts_only_the_order_id(self):
		with patch("buzz.hosted_payments.webhook_ping.make_post_request") as post:
			ping_site(order_id="HP-1", webhook_url="https://pro.example.com/webhook", generation=1)
		post.assert_called_once_with("https://pro.example.com/webhook", json={"order_id": "HP-1"}, timeout=30)

	def test_failed_ping_is_logged_not_raised(self):
		with (
			patch("requests.Session.request", side_effect=requests.ConnectionError),
			patch("frappe.log_error") as log_error,
		):
			ping_site(order_id="HP-1", webhook_url="https://pro.example.com/webhook", generation=1)
		log_error.assert_called_once()


class TestHostedRefunds(HostedPaymentsTestCase):
	def setUp(self):
		super().setUp()
		with self.set_user(self.integration):
			self.order_id = create_order(**self.order_values(amount=550)).order_id
		payment_testing.pay(frappe.db.get_value("Hosted Payment", self.order_id, "payment_request"))

	def refund(self, amount: float, user: str | None = None, idempotency_key: str | None = None):
		with self.set_user(user or self.integration):
			return refund(self.order_id, amount, idempotency_key or frappe.generate_hash())

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

	def test_refund_retried_with_its_key_returns_the_first_refund(self):
		first = self.refund(200, idempotency_key="PRO-RFND-1")
		retry = self.refund(200, idempotency_key="PRO-RFND-1")
		self.assertEqual((retry.refund_id, retry.status, retry.amount), (first.refund_id, "Processed", 200))
		self.assertEqual(self.refunded_amount(), 200)

	def test_refund_with_another_key_is_another_refund(self):
		first = self.refund(200, idempotency_key="PRO-RFND-1")
		second = self.refund(200, idempotency_key="PRO-RFND-2")
		self.assertNotEqual(second.refund_id, first.refund_id)
		self.assertEqual(self.refunded_amount(), 400)

	def test_refund_over_the_balance_is_rejected(self):
		self.refund(500)
		with self.assertRaises(RefundExceedsBalance):
			self.refund(100)
		self.assertEqual(self.refunded_amount(), 500)

	def test_refund_of_the_balance_is_compared_in_minor_units(self):
		self.refund(500)
		result = self.refund(50.004)
		self.assertEqual((result.status, result.amount), ("Processed", 50))
		self.assertEqual(self.refunded_amount(), 550)

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

	def test_pending_refund_is_refreshed_from_the_gateway_when_read(self):
		payment_testing.set_next_refund_status("Pending")
		pending = self.refund(200)
		payment_testing.set_refund_status(pending.refund_id, "Processed")
		settled = self.refund_status(pending.refund_id)
		self.assertEqual((settled.status, self.refunded_amount()), ("Processed", 200))

	def test_refund_whose_gateway_answer_was_lost_is_pending_and_made_once_when_read(self):
		payment_testing.lose_next_refund_answer()
		pending = self.refund(200)
		self.assertEqual((pending.status, pending.amount, self.refunded_amount()), ("Pending", 200, 0))
		settled = self.refund_status(pending.refund_id)
		self.assertEqual((settled.status, self.refunded_amount()), ("Processed", 200))
		self.assertEqual(len(StubRazorpayClient.created_refunds), 1)

	def test_refund_whose_gateway_answer_was_lost_keeps_its_amount_reserved(self):
		payment_testing.lose_next_refund_answer()
		self.refund(500)
		with self.assertRaises(RefundExceedsBalance):
			self.refund(100)

	def test_refund_retried_while_its_gateway_answer_is_lost_returns_the_pending_refund(self):
		payment_testing.lose_next_refund_answer()
		first = self.refund(200, idempotency_key="PRO-RFND-LOST")
		retry = self.refund(200, idempotency_key="PRO-RFND-LOST")
		self.assertEqual((retry.refund_id, retry.status), (first.refund_id, "Pending"))
		self.assertEqual(len(StubRazorpayClient.created_refunds), 1)

	def test_refund_whose_result_failed_to_record_after_the_gateway_made_it_is_pending(self):
		with patch.object(GatewayRefund, "apply_gateway_result", side_effect=frappe.TimestampMismatchError):
			pending = self.refund(500)
		self.assertEqual((pending.status, pending.amount), ("Pending", 500))
		with self.assertRaises(RefundExceedsBalance):
			self.refund(100)
		settled = self.refund_status(pending.refund_id)
		self.assertEqual((settled.status, self.refunded_amount()), ("Processed", 500))
		self.assertEqual(len(StubRazorpayClient.created_refunds), 1)

	def test_refund_the_gateway_refused_is_answered_failed_and_frees_its_amount(self):
		refused = frappe.ValidationError("Razorpay rejected the request: amount exceeds the payment")
		with patch.object(StubRazorpayClient, "create_refund", side_effect=refused):
			failed = self.refund(500)
		self.assertEqual((failed.status, failed.amount), ("Failed", 500))
		self.assertEqual(self.refund(550).status, "Processed")

	def test_full_refund_pings_the_site_once(self):
		pings = pings_after(lambda: self.refund(550))
		self.assertEqual([ping["order_id"] for ping in pings], [self.order_id])

	def test_second_partial_refund_settling_pings_the_site(self):
		self.refund(200)
		payment_testing.set_next_refund_status("Pending")
		pending = self.refund(100)
		pings = pings_after(lambda: payment_testing.send_refund_webhook(pending.refund_id, "Processed"))
		self.assertEqual([ping["order_id"] for ping in pings], [self.order_id])

	def test_refund_of_another_order_is_not_found(self):
		other_order = self.create_other_order()
		other_refund = self.refund(100)
		with self.set_user(self.integration), self.assertRaises(RefundNotFound):
			get_refund_status(other_order, other_refund.refund_id)

	def create_other_order(self) -> str:
		with self.set_user(self.integration):
			return create_order(**self.order_values()).order_id
