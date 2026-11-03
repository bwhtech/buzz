from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.payments import get_payment_link
from buzz.tests.base_test_cases import (
	attendee_rows,
	create_paid_ticket_type,
	create_payment_request,
	create_unpaid_payment,
	razorpay_gateway,
	run_gateway_callback,
)
from buzz.tests.factories import BuzzEventFactory, EventBookingFactory


class TestRazorpayPaymentVerification(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()
		cls.ticket_type = create_paid_ticket_type(cls.event.name, 500)
		cls.gateway = razorpay_gateway()

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))
		self.enterContext(patch("frappe.sendmail"))
		self.run_id = frappe.generate_hash(length=8)
		self.booking = self.create_booking()
		self.order_id = self.new_order_id()
		self.payment = create_unpaid_payment(self.booking, self.order_id)

	def new_order_id(self) -> str:
		return f"order_{frappe.generate_hash(length=10)}"

	def create_booking(self):
		return EventBookingFactory.create(
			event=self.event.name, attendees=attendee_rows(self.ticket_type.name, 1)
		)

	def pay(self, booking, payment_id: str, order_id: str | None, **gateway_payment):
		# Marking a payment received commits, so ids must not repeat between runs.
		create_payment_request(booking, razorpay_payment_id=f"{payment_id}_{self.run_id}")
		details = {
			"order_id": order_id,
			"amount": int(booking.total_amount * 100),
			"currency": booking.currency,
		}
		run_gateway_callback(booking, details | gateway_payment)

	def assert_unconfirmed(self, booking):
		self.assertEqual(frappe.db.get_value("Event Booking", booking.name, "docstatus"), 0)

	def test_payment_for_the_recorded_order_confirms_the_booking(self):
		self.pay(self.booking, "pay_correct", self.order_id)

		self.assertEqual(self.booking.docstatus, 1)
		payment = frappe.db.get_value(
			"Event Payment", self.payment.name, ["payment_received", "payment_id", "order_id"]
		)
		self.assertEqual(payment, (1, f"pay_correct_{self.run_id}", self.order_id))

	def test_total_the_order_truncated_to_paise_confirms_the_booking(self):
		frappe.db.set_value("Event Payment", self.payment.name, "amount", 1.13)

		self.pay(self.booking, "pay_truncated", self.order_id, amount=112, currency="INR")

		self.assertEqual(self.booking.docstatus, 1)

	def test_refuses_less_than_the_total_on_the_recorded_order(self):
		with self.assertRaises(frappe.ValidationError):
			self.pay(self.booking, "pay_small", self.order_id, amount=100)

		self.assert_unconfirmed(self.booking)

	def test_refuses_another_currency_on_the_recorded_order(self):
		with self.assertRaises(frappe.ValidationError):
			self.pay(self.booking, "pay_dollars", self.order_id, currency="USD")

		self.assert_unconfirmed(self.booking)

	def test_refuses_a_payment_for_another_order(self):
		with self.assertRaises(frappe.ValidationError):
			self.pay(self.booking, "pay_other", self.new_order_id())

		self.assert_unconfirmed(self.booking)

	def test_refuses_a_payment_with_no_order_when_the_row_has_none(self):
		frappe.db.set_value("Event Payment", self.payment.name, "order_id", None)

		with self.assertRaises(frappe.ValidationError):
			self.pay(self.booking, "pay_no_order", None)

		self.assert_unconfirmed(self.booking)

	def test_refuses_a_payment_already_used_for_another_booking(self):
		self.pay(self.booking, "pay_reused", self.order_id)
		other = self.create_booking()
		other_payment = create_unpaid_payment(other, self.new_order_id())

		with self.assertRaises(frappe.ValidationError):
			self.pay(other, "pay_reused", self.order_id)

		self.assert_unconfirmed(other)
		self.assertEqual(frappe.db.get_value("Event Payment", other_payment.name, "payment_received"), 0)

	def test_refuses_confirmation_without_an_integration_request(self):
		with self.assertRaises(frappe.ValidationError):
			run_gateway_callback(self.booking, {"order_id": self.order_id})

		self.assert_unconfirmed(self.booking)

	def test_refuses_confirmation_without_an_unpaid_payment(self):
		frappe.db.set_value("Event Payment", self.payment.name, "payment_received", 1)

		with self.assertRaises(frappe.ValidationError):
			self.pay(self.booking, "pay_orphan", self.order_id)

		self.assert_unconfirmed(self.booking)

	def test_gateway_named_by_the_client_does_not_skip_verification(self):
		create_payment_request(self.booking, razorpay_payment_id="pay_stripe", payment_gateway="Stripe")

		with self.assertRaises(frappe.ValidationError):
			run_gateway_callback(self.booking, {"order_id": self.new_order_id()})

		self.assert_unconfirmed(self.booking)

	def test_payment_link_records_the_razorpay_order_on_the_payment(self):
		controller = MagicMock()
		controller.create_order.return_value = {"id": "order_from_razorpay"}

		with patch("buzz.payments.get_controller", return_value=controller):
			get_payment_link("Event Booking", self.booking.name, 500, "INR", self.gateway)

		payment_name = frappe.get_last_doc(
			"Event Payment", {"reference_docname": self.booking.name, "name": ["!=", self.payment.name]}
		).name
		self.assertEqual(
			frappe.db.get_value("Event Payment", payment_name, "order_id"), "order_from_razorpay"
		)
