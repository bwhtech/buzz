import frappe

from buzz.payments import get_payment_link_for_booking
from buzz.tests.base_test_cases import BookingRefundTestCase


class TestPayingForABooking(BookingRefundTestCase):
	def test_a_confirmed_payment_submits_the_booking(self):
		self.assertEqual(
			(self.booking.docstatus, self.booking.status, self.booking.payment_status),
			(1, "Confirmed", "Paid"),
		)

	def test_a_confirmed_payment_is_recorded_against_the_booking(self):
		payment_request = frappe.get_doc("Gateway Payment Request", self.payment.payment_request)

		self.assertEqual(self.payment.payment_received, 1)
		self.assertEqual(
			(self.payment.payment_id, self.payment.order_id, self.payment.payment_gateway),
			(payment_request.gateway_transaction_ref, payment_request.order_ref, self.gateway),
		)

	def test_an_unpaid_booking_stays_a_draft(self):
		booking = self.create_booking(("Pending",), self.ticket_types[:1])

		get_payment_link_for_booking(booking.name)

		booking.reload()
		self.assertEqual((booking.docstatus, booking.payment_status), (0, "Unpaid"))
		self.assertEqual(self.get_payment(booking.name).payment_received, 0)

	def test_the_shopper_comes_back_to_the_page_buzz_asked_for(self):
		booking = self.create_booking(("Returning",), self.ticket_types[:1])

		get_payment_link_for_booking(booking.name, redirect_to="/b/booking-success/x?token=t")

		payment_request = self.get_payment(booking.name).payment_request
		self.assertEqual(
			frappe.db.get_value("Gateway Payment Request", payment_request, "redirect_to"),
			"/b/booking-success/x?token=t",
		)

	def test_the_gateway_gets_the_buyer_on_the_booking(self):
		booking = self.create_booking(("Buyer",), self.ticket_types[:1])
		booking.db_set(
			{"buyer_name": "Asha Rao Nair", "buyer_email": "asha@example.com", "buyer_phone": "+919876543210"}
		)
		booking.reload()

		with self.set_user("Guest"):
			get_payment_link_for_booking(booking.name)

		payment_request = frappe.get_doc(
			"Gateway Payment Request", self.get_payment(booking.name).payment_request
		)
		self.assertEqual(
			(
				payment_request.customer_email,
				payment_request.customer_phone,
				payment_request.customer_forenames,
				payment_request.customer_surname,
			),
			("asha@example.com", "+919876543210", "Asha", "Rao Nair"),
		)
