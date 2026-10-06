import frappe

from buzz.api.booking import get_booking_confirmation, process_booking
from buzz.api.booking.services import get_booking_access_token, verify_booking_access_token
from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import EventBookingFactory, EventTicketTypeFactory


class TestBookingConfirmation(BookingTestCase):
	def test_access_token_roundtrip(self):
		token = get_booking_access_token("B-TEST-001")

		self.assertTrue(verify_booking_access_token("B-TEST-001", token))
		for wrong_token in ("deadbeef", "", None):
			self.assertFalse(verify_booking_access_token("B-TEST-001", wrong_token))
		self.assertFalse(verify_booking_access_token("B-OTHER-002", token))

	def test_free_booking_redirects_to_the_token_gated_success_page(self):
		payload = process_booking(self.booking_request())

		path, token = payload.redirect_to.split("?token=")
		self.assertEqual(path, f"/booking-success/{payload.booking_name}")
		self.assertTrue(verify_booking_access_token(payload.booking_name, token))

	def test_free_booking_confirms_on_submit(self):
		booking = self.create_booking(self.free_ticket_type.name)

		booking.submit()

		self.assertEqual(
			(booking.status, booking.payment_status, booking.total_amount), ("Confirmed", "Paid", 0)
		)

	def test_guest_with_a_valid_token_sees_the_booking(self):
		booking = self.create_submitted_booking()
		token = get_booking_access_token(booking.name)

		with self.set_user("Guest"):
			result = get_booking_confirmation(booking.name, token=token)

		self.assertEqual(result.booking.name, booking.name)
		self.assertEqual([ticket.attendee_name for ticket in result.tickets], ["Conf"])
		self.assertEqual(result.event.title, self.event.title)

	def test_guest_with_a_bad_token_is_refused(self):
		booking = self.create_submitted_booking()

		with self.set_user("Guest"):
			for token in ("wrong-token", ""):
				with self.subTest(token=token), self.assertRaises(frappe.PermissionError):
					get_booking_confirmation(booking.name, token=token)

	def test_a_user_with_access_needs_no_token(self):
		booking = self.create_submitted_booking()

		self.assertEqual(get_booking_confirmation(booking.name).booking.name, booking.name)

	def create_submitted_booking(self):
		paid_ticket_type = EventTicketTypeFactory.create(
			event=self.event.name, prices=[{"currency": "INR", "price": 500}]
		).name
		booking = self.create_booking(paid_ticket_type)
		booking.submit()
		return booking

	def create_booking(self, ticket_type: str):
		attendees = [{"ticket_type": ticket_type, "first_name": "Conf", "email": "conf@example.com"}]
		return EventBookingFactory.create(event=self.event.name, attendees=attendees)
