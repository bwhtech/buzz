from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.tickets import (
	change_add_on_preference,
	create_cancellation_request,
	get_ticket_details,
	transfer_ticket,
)
from buzz.api.tickets.exceptions import (
	AddOnChangeWindowClosed,
	AddOnValueNotFound,
	CancellationAlreadyRequested,
	CancellationNotPermitted,
	CancellationWindowClosed,
	TicketNotAccessible,
	TicketNotFound,
	TicketNotInBooking,
	TransferNotPermitted,
	TransferWindowClosed,
)
from buzz.api.tickets.windows import TRANSFER, is_window_open

ATTENDEE = "ticket-attendee@example.com"
OTHER_USER = "ticket-outsider@example.com"

DETAILS_FIELDS = {
	"doc",
	"add_ons",
	"event",
	"booking",
	"ticket_type",
	"can_transfer_ticket",
	"can_change_add_ons",
	"can_request_cancellation",
	"zoom_join_url",
	"zoom_reference_doctype",
	"zoom_reference_name",
}


class TicketTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		for email, first_name in ((ATTENDEE, "Ticket"), (OTHER_USER, "Outsider")):
			if not frappe.db.exists("User", email):
				frappe.get_doc(
					{"doctype": "User", "email": email, "first_name": first_name, "send_welcome_email": 0}
				).insert(ignore_permissions=True)

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()
		# The window checks read Buzz Settings, so pin the cutoffs the tests reason about.
		self.set_cutoffs(7)
		self.ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event.name,
				"title": f"Tickets Test {frappe.generate_hash(length=6)}",
				"price": 100,
			}
		).insert(ignore_permissions=True)

	def set_cutoffs(self, days):
		for fieldname in (
			"allow_transfer_ticket_before_event_start_days",
			"allow_add_ons_change_before_event_start_days",
			"allow_ticket_cancellation_request_before_event_start_days",
		):
			frappe.db.set_single_value("Buzz Settings", fieldname, days)
		frappe.clear_document_cache("Buzz Settings", "Buzz Settings")

	def set_event_start(self, days_from_today):
		start_date = add_days(today(), days_from_today)
		frappe.db.set_value("Buzz Event", self.event.name, {"start_date": start_date, "end_date": start_date})
		frappe.clear_document_cache("Buzz Event", self.event.name)

	def make_ticket(self, attendee_email=ATTENDEE, booking=None):
		return frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"event": self.event.name,
				"ticket_type": self.ticket_type.name,
				"attendee_name": "Ticket Attendee",
				"attendee_email": attendee_email,
				"booking": booking,
			}
		).insert(ignore_permissions=True)

	def make_booking(self, user=ATTENDEE):
		# Event Booking.validate prices the attendee rows, so it needs at least one.
		return frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event.name,
				"user": user,
				"attendees": [
					{"ticket_type": self.ticket_type.name, "first_name": "Ticket", "email": ATTENDEE}
				],
			}
		).insert(ignore_permissions=True)


class TestWindows(TicketTestCase):
	def test_open_while_the_event_is_beyond_the_cutoff(self):
		self.set_event_start(30)
		self.assertTrue(is_window_open(self.event.name, TRANSFER))

	def test_closed_once_inside_the_cutoff(self):
		self.set_event_start(3)
		self.assertFalse(is_window_open(self.event.name, TRANSFER))

	def test_exactly_on_the_cutoff_is_still_open(self):
		self.set_event_start(7)
		self.assertTrue(is_window_open(self.event.name, TRANSFER))

	def test_a_zero_cutoff_keeps_the_window_open_until_the_day(self):
		# Regression: a 0 cutoff must stay 0, not fall back to the 7-day default.
		self.set_cutoffs(0)
		self.set_event_start(1)
		self.assertTrue(is_window_open(self.event.name, TRANSFER))

	def test_an_event_without_a_start_date_is_closed(self):
		self.set_event_start(30)
		frappe.db.set_value("Buzz Event", self.event.name, "start_date", None)
		frappe.clear_document_cache("Buzz Event", self.event.name)
		self.assertFalse(is_window_open(self.event.name, TRANSFER))


class TestGetTicketDetails(TicketTestCase):
	def test_shape(self):
		self.set_event_start(30)
		ticket = self.make_ticket()
		frappe.set_user(ATTENDEE)

		details = get_ticket_details(ticket.name)
		self.assertEqual(set(details.__json__()), DETAILS_FIELDS)
		self.assertEqual(details.doc.name, ticket.name)
		self.assertEqual(details.add_ons, [])
		self.assertIsNone(details.booking)
		self.assertIsNone(details.zoom_join_url)

	def test_window_flags_are_plain_booleans(self):
		self.set_event_start(30)
		ticket = self.make_ticket()
		frappe.set_user(ATTENDEE)

		details = get_ticket_details(ticket.name)
		self.assertIs(details.can_transfer_ticket, True)
		self.assertIs(details.can_change_add_ons, True)
		self.assertIs(details.can_request_cancellation, True)

	def test_window_flags_go_false_near_the_event(self):
		self.set_event_start(2)
		ticket = self.make_ticket()
		frappe.set_user(ATTENDEE)

		details = get_ticket_details(ticket.name)
		self.assertIs(details.can_transfer_ticket, False)
		self.assertIs(details.can_change_add_ons, False)
		self.assertIs(details.can_request_cancellation, False)

	def test_another_user_cannot_read_the_ticket(self):
		self.set_event_start(30)
		ticket = self.make_ticket()
		frappe.set_user(OTHER_USER)

		with self.assertRaises(TicketNotAccessible):
			get_ticket_details(ticket.name)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Not Permitted")

	def test_booking_is_withheld_from_an_attendee_who_did_not_book(self):
		self.set_event_start(30)
		booking = self.make_booking(user=OTHER_USER)
		ticket = self.make_ticket(booking=booking.name)
		frappe.set_user(ATTENDEE)

		self.assertIsNone(get_ticket_details(ticket.name).booking)


class TestTransferTicket(TicketTestCase):
	def setUp(self):
		super().setUp()
		self.set_event_start(30)

	@patch("buzz.api.tickets.services.send_ticket_transfer_emails")
	def test_attendee_transfers_their_own_ticket(self, mock_emails):
		ticket = self.make_ticket()
		frappe.set_user(ATTENDEE)

		transfer_ticket(ticket.name, "New", "Owner", "new-owner@example.com")

		ticket.reload()
		self.assertEqual(ticket.attendee_email, "new-owner@example.com")
		self.assertEqual(ticket.attendee_name, "New Owner")
		mock_emails.assert_called_once()

	@patch("buzz.api.tickets.services.send_ticket_transfer_emails")
	def test_booking_owner_may_transfer(self, mock_emails):
		booking = self.make_booking(user=OTHER_USER)
		ticket = self.make_ticket(booking=booking.name)
		frappe.set_user(OTHER_USER)

		transfer_ticket(ticket.name, "New", "Owner", "new-owner@example.com")
		self.assertEqual(
			frappe.db.get_value("Event Ticket", ticket.name, "attendee_email"), "new-owner@example.com"
		)

	def test_unknown_ticket(self):
		with self.assertRaises(TicketNotFound):
			transfer_ticket("not-a-ticket", "New", "Owner", "new-owner@example.com")

		self.assertEqual(TicketNotFound.http_status_code, 404)

	def test_an_unrelated_user_cannot_transfer(self):
		ticket = self.make_ticket()
		frappe.set_user(OTHER_USER)

		with self.assertRaises(TransferNotPermitted):
			transfer_ticket(ticket.name, "New", "Owner", "new-owner@example.com")

		self.assertEqual(TransferNotPermitted.http_status_code, 403)

	def test_transfer_is_refused_once_the_window_closes(self):
		ticket = self.make_ticket()
		self.set_event_start(2)
		frappe.set_user(ATTENDEE)

		with self.assertRaises(TransferWindowClosed):
			transfer_ticket(ticket.name, "New", "Owner", "new-owner@example.com")

		self.assertEqual(TransferWindowClosed.http_status_code, 409)
		self.assertEqual(frappe.local.message_log[-1]["title"], "Transfers Closed")


class TestChangeAddOnPreference(TicketTestCase):
	def setUp(self):
		super().setUp()
		self.set_event_start(30)
		self.add_on = frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": self.event.name,
				"title": f"Meal {frappe.generate_hash(length=6)}",
				"user_selects_option": 1,
				"options": "Veg\nNon-veg",
				"price": 0,
				"currency": "INR",
			}
		).insert(ignore_permissions=True)

	def make_ticket_with_add_on(self, value="Veg"):
		ticket = self.make_ticket()
		ticket.append("add_ons", {"add_on": self.add_on.name, "value": value, "price": 0, "currency": "INR"})
		ticket.save(ignore_permissions=True)
		return ticket, ticket.add_ons[0].name

	def test_changes_the_stored_value(self):
		ticket, add_on_value_id = self.make_ticket_with_add_on()
		change_add_on_preference(add_on_value_id, "Non-veg")
		self.assertEqual(frappe.db.get_value("Ticket Add-on Value", add_on_value_id, "value"), "Non-veg")

	def test_unknown_add_on_value(self):
		with self.assertRaises(AddOnValueNotFound):
			change_add_on_preference("not-an-add-on-value", "Non-veg")

		self.assertEqual(AddOnValueNotFound.http_status_code, 404)

	def test_refused_once_the_window_closes(self):
		ticket, add_on_value_id = self.make_ticket_with_add_on()
		self.set_event_start(2)

		with self.assertRaises(AddOnChangeWindowClosed):
			change_add_on_preference(add_on_value_id, "Non-veg")

		self.assertEqual(AddOnChangeWindowClosed.http_status_code, 409)

	def test_details_carry_the_selectable_options(self):
		ticket, _ = self.make_ticket_with_add_on()
		frappe.set_user(ATTENDEE)

		add_ons = get_ticket_details(ticket.name).add_ons
		self.assertEqual(len(add_ons), 1)
		self.assertEqual(add_ons[0].options, ["Veg", "Non-veg"])
		self.assertEqual(add_ons[0].value, "Veg")
		# Check fields travel as 0/1, not booleans.
		self.assertEqual(add_ons[0].user_selects_option, 1)


class TestCreateCancellationRequest(TicketTestCase):
	def setUp(self):
		super().setUp()
		self.set_event_start(30)
		self.booking = self.make_booking()

	def test_full_booking_request(self):
		self.make_ticket(booking=self.booking.name)
		frappe.set_user(ATTENDEE)

		create_cancellation_request(self.booking.name)

		request = frappe.get_last_doc("Ticket Cancellation Request", filters={"booking": self.booking.name})
		self.assertTrue(request.cancel_full_booking)
		self.assertEqual(request.tickets, [])

	def test_partial_request_records_the_named_tickets(self):
		first = self.make_ticket(booking=self.booking.name)
		self.make_ticket(booking=self.booking.name)
		frappe.set_user(ATTENDEE)

		create_cancellation_request(self.booking.name, [first.name])

		request = frappe.get_last_doc("Ticket Cancellation Request", filters={"booking": self.booking.name})
		self.assertFalse(request.cancel_full_booking)
		self.assertEqual([row.ticket for row in request.tickets], [first.name])

	def test_naming_every_ticket_is_treated_as_a_full_cancellation(self):
		first = self.make_ticket(booking=self.booking.name)
		second = self.make_ticket(booking=self.booking.name)
		frappe.set_user(ATTENDEE)

		create_cancellation_request(self.booking.name, [first.name, second.name])

		request = frappe.get_last_doc("Ticket Cancellation Request", filters={"booking": self.booking.name})
		self.assertTrue(request.cancel_full_booking)

	def test_a_ticket_from_another_booking_is_refused(self):
		# Two tickets on the booking, so naming one stray id stays on the partial path —
		# a count match short-circuits to a full-booking request before the check runs.
		self.make_ticket(booking=self.booking.name)
		self.make_ticket(booking=self.booking.name)
		other_booking = self.make_booking()
		stray = self.make_ticket(booking=other_booking.name)
		frappe.set_user(ATTENDEE)

		with self.assertRaises(TicketNotInBooking):
			create_cancellation_request(self.booking.name, [stray.name])

		self.assertIn(stray.name, frappe.local.message_log[-1]["message"])

	def test_another_user_cannot_request(self):
		self.make_ticket(booking=self.booking.name)
		frappe.set_user(OTHER_USER)

		with self.assertRaises(CancellationNotPermitted):
			create_cancellation_request(self.booking.name)

		self.assertEqual(CancellationNotPermitted.http_status_code, 403)

	def test_refused_once_the_window_closes(self):
		self.make_ticket(booking=self.booking.name)
		self.set_event_start(2)
		frappe.set_user(ATTENDEE)

		with self.assertRaises(CancellationWindowClosed):
			create_cancellation_request(self.booking.name)

		self.assertEqual(CancellationWindowClosed.http_status_code, 409)

	def test_a_second_open_request_is_refused(self):
		self.make_ticket(booking=self.booking.name)
		frappe.set_user(ATTENDEE)
		create_cancellation_request(self.booking.name)

		with self.assertRaises(CancellationAlreadyRequested):
			create_cancellation_request(self.booking.name)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Already Requested")
