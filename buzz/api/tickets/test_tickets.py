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
from buzz.api.tickets.windows import ADD_ON_CHANGE, CANCELLATION, TRANSFER
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	EventBookingFactory,
	EventTicketFactory,
	TicketAddOnFactory,
	UserFactory,
)

ATTENDEE = "ticket-attendee@example.com"
OTHER_USER = "ticket-outsider@example.com"


class TicketTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()
		UserFactory.create_once(ATTENDEE)
		UserFactory.create_once(OTHER_USER)

	def setUp(self):
		frappe.clear_messages()
		# The rollback restores these rows but not their cached copies.
		self.addCleanup(frappe.clear_document_cache, "Buzz Team Settings", self.event.team)
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event.name)
		# The window checks read the team's cutoffs.
		self.set_cutoffs(7)
		self.set_event_start(30)

	def set_cutoffs(self, days: int):
		BuzzTeamFactory.set_settings(
			self.event.team, dict.fromkeys((TRANSFER, ADD_ON_CHANGE, CANCELLATION), days)
		)

	def set_event_start(self, days_from_today: int):
		start_date = add_days(today(), days_from_today)
		frappe.db.set_value("Buzz Event", self.event.name, {"start_date": start_date, "end_date": start_date})
		frappe.clear_document_cache("Buzz Event", self.event.name)

	def make_ticket(self, attendee_email: str = ATTENDEE, booking: str | None = None, **overrides):
		return EventTicketFactory.create(
			event=self.event.name, attendee_email=attendee_email, booking=booking, **overrides
		)

	def make_booking(self, user: str = ATTENDEE):
		return EventBookingFactory.create(event=self.event.name, user=user)


class TestGetTicketDetails(TicketTestCase):
	def test_window_flags_go_false_near_the_event(self):
		self.set_event_start(2)
		ticket = self.make_ticket()

		with self.set_user(ATTENDEE):
			details = get_ticket_details(ticket.name)

		self.assertIs(details.can_transfer_ticket, False)
		self.assertIs(details.can_change_add_ons, False)
		self.assertIs(details.can_request_cancellation, False)

	def test_another_user_cannot_read_the_ticket(self):
		ticket = self.make_ticket()

		with self.set_user(OTHER_USER), self.assertRaises(TicketNotAccessible):
			get_ticket_details(ticket.name)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Not Permitted")

	def test_booker_can_read_a_ticket_held_by_someone_else(self):
		booking = self.make_booking(user=OTHER_USER)
		ticket = self.make_ticket(attendee_email="guest@example.com", booking=booking.name)

		with self.set_user(OTHER_USER):
			details = get_ticket_details(ticket.name)

		self.assertEqual(details.doc.name, ticket.name)
		self.assertEqual(details.booking.name, booking.name)

	def test_booking_is_withheld_from_an_attendee_who_did_not_book(self):
		booking = self.make_booking(user=OTHER_USER)
		ticket = self.make_ticket(booking=booking.name)

		with self.set_user(ATTENDEE):
			self.assertIsNone(get_ticket_details(ticket.name).booking)


class TestTransferTicket(TicketTestCase):
	@patch("buzz.api.tickets.services.send_ticket_transfer_emails")
	def test_attendee_transfers_their_own_ticket(self, mock_emails):
		ticket = self.make_ticket()

		with self.set_user(ATTENDEE):
			transfer_ticket(ticket.name, "New", "Owner", "new-owner@example.com")

		ticket.reload()
		self.assertEqual(ticket.attendee_email, "new-owner@example.com")
		self.assertEqual(ticket.attendee_name, "New Owner")
		mock_emails.assert_called_once()

	@patch("buzz.api.tickets.services.send_ticket_transfer_emails")
	def test_booking_owner_may_transfer(self, mock_emails):
		booking = self.make_booking(user=OTHER_USER)
		ticket = self.make_ticket(booking=booking.name)

		with self.set_user(OTHER_USER):
			transfer_ticket(ticket.name, "New", "Owner", "new-owner@example.com")

		self.assertEqual(
			frappe.db.get_value("Event Ticket", ticket.name, "attendee_email"), "new-owner@example.com"
		)

	def test_unknown_ticket(self):
		with self.assertRaises(TicketNotFound):
			transfer_ticket("not-a-ticket", "New", "Owner", "new-owner@example.com")

	def test_an_unrelated_user_cannot_transfer(self):
		ticket = self.make_ticket()

		with self.set_user(OTHER_USER), self.assertRaises(TransferNotPermitted):
			transfer_ticket(ticket.name, "New", "Owner", "new-owner@example.com")

	def test_transfer_is_refused_once_the_window_closes(self):
		ticket = self.make_ticket()
		self.set_event_start(2)

		with self.set_user(ATTENDEE), self.assertRaises(TransferWindowClosed):
			transfer_ticket(ticket.name, "New", "Owner", "new-owner@example.com")

		self.assertEqual(frappe.local.message_log[-1]["title"], "Transfers Closed")


class TestChangeAddOnPreference(TicketTestCase):
	def setUp(self):
		super().setUp()
		self.add_on = TicketAddOnFactory.create(
			event=self.event.name, user_selects_option=1, options="Veg\nNon-veg"
		)

	def test_changes_the_stored_value(self):
		add_on_value = self.make_ticket_with_add_on().add_ons[0].name

		change_add_on_preference(add_on_value, "Non-veg")

		self.assertEqual(frappe.db.get_value("Ticket Add-on Value", add_on_value, "value"), "Non-veg")

	def test_unknown_add_on_value(self):
		with self.assertRaises(AddOnValueNotFound):
			change_add_on_preference("not-an-add-on-value", "Non-veg")

	def test_refused_once_the_window_closes(self):
		add_on_value = self.make_ticket_with_add_on().add_ons[0].name
		self.set_event_start(2)

		with self.assertRaises(AddOnChangeWindowClosed):
			change_add_on_preference(add_on_value, "Non-veg")

	def test_details_carry_the_selectable_options(self):
		ticket = self.make_ticket_with_add_on(value="Veg")

		with self.set_user(ATTENDEE):
			add_ons = get_ticket_details(ticket.name).add_ons

		self.assertEqual(len(add_ons), 1)
		self.assertEqual(add_ons[0].options, ["Veg", "Non-veg"])
		self.assertEqual(add_ons[0].value, "Veg")
		# Check fields travel as 0/1, not booleans.
		self.assertEqual(add_ons[0].user_selects_option, 1)

	def make_ticket_with_add_on(self, value: str = "Veg"):
		add_on = {"add_on": self.add_on.name, "value": value, "price": 0, "currency": "INR"}
		return self.make_ticket(add_ons=[add_on])


class TestCreateCancellationRequest(TicketTestCase):
	def setUp(self):
		super().setUp()
		self.booking = self.make_booking().name

	def test_full_booking_request(self):
		self.make_ticket(booking=self.booking)

		with self.set_user(ATTENDEE):
			create_cancellation_request(self.booking)

		request = self.last_cancellation_request()
		self.assertTrue(request.cancel_full_booking)
		self.assertEqual(request.tickets, [])

	def test_partial_request_records_the_named_tickets(self):
		first = self.make_ticket(booking=self.booking).name
		self.make_ticket(booking=self.booking)

		with self.set_user(ATTENDEE):
			create_cancellation_request(self.booking, [first])

		request = self.last_cancellation_request()
		self.assertFalse(request.cancel_full_booking)
		self.assertEqual([row.ticket for row in request.tickets], [first])

	def test_naming_every_ticket_is_treated_as_a_full_cancellation(self):
		first = self.make_ticket(booking=self.booking).name
		second = self.make_ticket(booking=self.booking).name

		with self.set_user(ATTENDEE):
			create_cancellation_request(self.booking, [first, second])

		self.assertTrue(self.last_cancellation_request().cancel_full_booking)

	def test_a_ticket_from_another_booking_is_refused(self):
		# Two tickets keep the request partial: a count match skips the booking check.
		self.make_ticket(booking=self.booking)
		self.make_ticket(booking=self.booking)
		other_booking_ticket = self.make_ticket(booking=self.make_booking().name).name

		with self.set_user(ATTENDEE), self.assertRaises(TicketNotInBooking):
			create_cancellation_request(self.booking, [other_booking_ticket])

		self.assertIn(other_booking_ticket, frappe.local.message_log[-1]["message"])

	def test_another_user_cannot_request(self):
		self.make_ticket(booking=self.booking)

		with self.set_user(OTHER_USER), self.assertRaises(CancellationNotPermitted):
			create_cancellation_request(self.booking)

	def test_refused_once_the_window_closes(self):
		self.make_ticket(booking=self.booking)
		self.set_event_start(2)

		with self.set_user(ATTENDEE), self.assertRaises(CancellationWindowClosed):
			create_cancellation_request(self.booking)

	def test_a_second_open_request_is_refused(self):
		self.make_ticket(booking=self.booking)

		with self.set_user(ATTENDEE):
			create_cancellation_request(self.booking)
			with self.assertRaises(CancellationAlreadyRequested):
				create_cancellation_request(self.booking)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Already Requested")

	def last_cancellation_request(self):
		return frappe.get_last_doc("Ticket Cancellation Request", filters={"booking": self.booking})
