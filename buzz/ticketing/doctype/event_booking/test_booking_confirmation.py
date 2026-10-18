from contextlib import ExitStack
from unittest.mock import patch

import frappe

from buzz.api.booking import (
	download_tickets,
	get_booking_confirmation,
	get_calendar_invite,
	process_booking,
)
from buzz.api.booking.downloads import inlined_qr
from buzz.api.booking.services import get_booking_access_token, verify_booking_access_token
from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import (
	EventBookingFactory,
	EventPaymentFactory,
	EventTicketTypeFactory,
	PaymentGatewayFactory,
)


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

	def test_confirmation_names_the_gateway_an_online_payment_went_through(self):
		booking = self.create_submitted_booking()
		gateway = PaymentGatewayFactory.create().name
		EventPaymentFactory.create(
			"received",
			reference_doctype="Event Booking",
			reference_docname=booking.name,
			payment_gateway=gateway,
		)

		self.assertEqual(get_booking_confirmation(booking.name).booking.payment_method, gateway)

	def test_guest_with_a_valid_token_downloads_the_calendar_invite(self):
		booking = self.create_submitted_booking()
		token = get_booking_access_token(booking.name)

		with self.set_user("Guest"):
			get_calendar_invite(booking.name, token=token)

		self.assertEqual(frappe.response.type, "download")
		self.assertEqual(frappe.response.filename, f"{self.event.title}.ics")
		self.assertIn(f"SUMMARY:{self.event.title}", frappe.response.filecontent)

	def test_guest_with_a_bad_token_gets_no_calendar_invite(self):
		booking = self.create_submitted_booking()

		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			get_calendar_invite(booking.name, token="wrong-token")

	def test_guest_with_a_valid_token_downloads_the_tickets(self):
		booking = self.create_submitted_booking()
		token = get_booking_access_token(booking.name)

		with self.set_user("Guest"), stub_pdf_rendering():
			download_tickets(booking.name, token=token)

		self.assertEqual(frappe.response.filename, f"Tickets-{booking.name}.pdf")
		self.assertTrue(frappe.response.filecontent.startswith(b"%PDF"))
		self.assertFalse(frappe.flags.ignore_print_permissions)

	def test_tickets_print_with_the_qr_inlined_and_the_stored_file_untouched(self):
		booking = self.create_submitted_booking()
		ticket = frappe.db.get_value(
			"Event Ticket", {"booking": booking.name}, ["name", "qr_code"], as_dict=True
		)

		self.assertTrue(inlined_qr(ticket.name).qr_code.startswith("data:image/png;base64,"))
		self.assertEqual(frappe.db.get_value("Event Ticket", ticket.name, "qr_code"), ticket.qr_code)

	def test_a_token_opens_only_its_own_booking(self):
		booking = self.create_submitted_booking()
		other_token = get_booking_access_token(self.create_submitted_booking().name)

		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			download_tickets(booking.name, token=other_token)

	def test_a_signed_in_outsider_gets_no_tickets(self):
		booking = self.create_submitted_booking()

		with self.set_user(self.outsider), self.assertRaises(frappe.PermissionError):
			download_tickets(booking.name)

	def create_submitted_booking(self):
		paid_ticket_type = EventTicketTypeFactory.create("paid", event=self.event.name).name
		booking = self.create_booking(paid_ticket_type)
		booking.submit()
		return booking

	def create_booking(self, ticket_type: str):
		attendees = [{"ticket_type": ticket_type, "first_name": "Conf", "email": "conf@example.com"}]
		return EventBookingFactory.create(event=self.event.name, attendees=attendees)


def stub_pdf_rendering() -> ExitStack:
	# CI never runs bench build, so printview has no assets.json and wkhtmltopdf
	# has no server to fetch the print styles from
	stack = ExitStack()
	stack.enter_context(patch("frappe.utils.get_assets_json", return_value={}))
	stack.enter_context(patch("frappe.utils.pdf.get_pdf", side_effect=add_blank_page))
	return stack


def add_blank_page(html: str, options=None, output=None):
	output.add_blank_page(width=100, height=100)
	return output
