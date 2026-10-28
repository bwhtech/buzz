from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.base_test_cases import attendee_rows, create_paid_ticket_type, razorpay_gateway
from buzz.tests.factories import (
	BuzzEventFactory,
	EventBookingFactory,
	EventPaymentFactory,
	IntegrationRequestFactory,
)

CONTROLLER = "buzz.payments.get_controller"


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
		self.payment = self.create_payment(self.booking)

	def create_booking(self):
		return EventBookingFactory.create(
			event=self.event.name, attendees=attendee_rows(self.ticket_type.name, 1)
		)

	def create_payment(self, booking):
		return EventPaymentFactory.create(
			user=booking.user,
			amount=booking.total_amount,
			currency=booking.currency,
			reference_doctype="Event Booking",
			reference_docname=booking.name,
			payment_gateway=self.gateway,
		)

	def create_request(self, booking, payment_id: str, payment_gateway: str | None = None):
		"""The Integration Request the payments app builds, with client-chosen values merged in."""
		data = {"razorpay_payment_id": payment_id, "payment_gateway": payment_gateway or self.gateway}
		IntegrationRequestFactory.create(
			reference_doctype="Event Booking", reference_docname=booking.name, data=frappe.as_json(data)
		)

	def authorize(self, booking, gateway_payment: dict):
		controller = MagicMock()
		controller.fetch_payment.return_value = gateway_payment
		with patch(CONTROLLER, return_value=controller):
			booking.on_payment_authorized("Completed")

	def pay(self, booking, payment_id: str, **gateway_payment):
		# Marking a payment received commits, so ids must not repeat between runs.
		payment_id = f"{payment_id}_{self.run_id}"
		self.create_request(booking, payment_id)
		details = {"amount": round(booking.total_amount * 100), "currency": booking.currency}
		self.authorize(booking, details | gateway_payment)

	def assert_unconfirmed(self, booking):
		self.assertEqual(frappe.db.get_value("Event Booking", booking.name, "docstatus"), 0)

	def test_correct_payment_confirms_the_booking(self):
		self.pay(self.booking, "pay_correct")

		self.assertEqual(self.booking.docstatus, 1)
		payment = frappe.db.get_value("Event Payment", self.payment.name, ["payment_received", "payment_id"])
		self.assertEqual(payment, (1, f"pay_correct_{self.run_id}"))

	def test_refuses_a_payment_for_less_than_the_total(self):
		with self.assertRaises(frappe.ValidationError):
			self.pay(self.booking, "pay_small", amount=100)

		self.assert_unconfirmed(self.booking)

	def test_refuses_a_payment_in_another_currency(self):
		with self.assertRaises(frappe.ValidationError):
			self.pay(self.booking, "pay_dollars", currency="USD")

		self.assert_unconfirmed(self.booking)

	def test_refuses_a_payment_id_already_used_for_another_booking(self):
		self.pay(self.booking, "pay_reused")
		other = self.create_booking()
		other_payment = self.create_payment(other)

		with self.assertRaises(frappe.ValidationError):
			self.pay(other, "pay_reused")

		self.assert_unconfirmed(other)
		self.assertEqual(frappe.db.get_value("Event Payment", other_payment.name, "payment_received"), 0)

	def test_gateway_named_by_the_client_does_not_skip_verification(self):
		self.create_request(self.booking, "pay_stripe", payment_gateway="Stripe")

		with self.assertRaises(frappe.ValidationError):
			self.authorize(self.booking, {"amount": 100, "currency": self.booking.currency})

		self.assert_unconfirmed(self.booking)
