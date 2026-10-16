from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime

from buzz.api.booking import hold_tickets, process_booking, release_hold
from buzz.api.booking.exceptions import RegistrationsClosed, TicketsUnavailable
from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import BuzzEventFactory, EventTicketTypeFactory, TicketHoldFactory


class HoldTestCase(BookingTestCase):
	def setUp(self):
		super().setUp()
		self.ticket_type = EventTicketTypeFactory.create(event=self.event.name, max_tickets_available=10)
		self.name = str(self.ticket_type.name)

	def hold(self, quantity: int, hold_token: str | None = None):
		return hold_tickets(self.event.name, {self.name: quantity}, hold_token)

	def held_by_others(self, quantity: int):
		TicketHoldFactory.create(ticket_type=self.ticket_type.name, quantity=quantity)

	def book(self, quantity: int, hold_token: str | None = None):
		attendees = [
			{"first_name": f"Booker {index}", "email": "booker@example.com", "ticket_type": self.name}
			for index in range(quantity)
		]
		return process_booking(self.booking_request(attendees=attendees, hold_token=hold_token))

	def holds_of(self, hold_token: str) -> int:
		return frappe.db.count("Ticket Hold", {"hold_token": hold_token})


class TestHoldTickets(HoldTestCase):
	def test_holds_what_others_have_not_held(self):
		self.held_by_others(5)

		with self.freeze_time(now_datetime()):
			response = self.hold(5)

		self.assertEqual(response.remaining, {self.name: 5})
		self.assertEqual(response.expires_in_seconds, 600)
		self.assertEqual(self.ticket_type.remaining_tickets, 0)

	def test_refuses_more_than_is_left(self):
		self.held_by_others(5)

		with self.assertRaises(TicketsUnavailable) as context:
			self.hold(6)
		self.assertIn("Only 5", str(context.exception))

	def test_a_resize_keeps_the_expiry(self):
		start = now_datetime()
		with self.freeze_time(start):
			token = self.hold(2).hold_token
		with self.freeze_time(add_to_date(start, minutes=3)):
			grown = self.hold(4, token)
			shrunk = self.hold(1, token)

		self.assertEqual(grown.hold_token, token)
		self.assertEqual(grown.expires_in_seconds, 420)
		self.assertEqual(shrunk.expires_in_seconds, 420)
		self.assertEqual(self.ticket_type.remaining_tickets, 9)

	def test_a_lapsed_token_gets_a_new_hold(self):
		token = self.hold(2).hold_token

		with self.freeze_time(add_to_date(now_datetime(), minutes=11)):
			response = self.hold(2, token)

		self.assertNotEqual(response.hold_token, token)
		self.assertEqual(self.holds_of(token), 0)

	def test_ticket_types_without_a_limit_hold_nothing(self):
		unlimited = str(EventTicketTypeFactory.create(event=self.event.name).name)

		response = hold_tickets(self.event.name, {unlimited: 3})

		self.assertEqual(response.remaining, {})
		self.assertIsNone(response.expires_in_seconds)
		self.assertEqual(self.holds_of(response.hold_token), 0)

	def test_refuses_another_events_ticket_type(self):
		other = EventTicketTypeFactory.create(event=BuzzEventFactory.create().name, max_tickets_available=5)

		with self.assertRaises(frappe.ValidationError):
			hold_tickets(self.event.name, {str(other.name): 1})

	def test_refuses_an_unpublished_ticket_type(self):
		unpublished = EventTicketTypeFactory.create("unpublished", event=self.event.name)

		with self.assertRaises(frappe.ValidationError):
			hold_tickets(self.event.name, {str(unpublished.name): 1})

	def test_refuses_closed_registrations(self):
		self.set_event({"registrations_close_at": add_to_date(now_datetime(), days=-1)})

		with self.assertRaises(RegistrationsClosed):
			self.hold(1)

	def test_refuses_guests_when_the_event_needs_a_login(self):
		with self.set_user("Guest"), self.assertRaises(frappe.AuthenticationError):
			self.hold(1)


class TestReleaseHold(HoldTestCase):
	def test_frees_the_tickets_at_once(self):
		token = self.hold(4).hold_token

		release_hold(token)

		self.assertEqual(self.ticket_type.remaining_tickets, 10)

	def test_releasing_twice_or_an_unknown_token_does_nothing(self):
		token = self.hold(4).hold_token

		release_hold(token)
		release_hold(token)
		release_hold("unknown-token")

		self.assertEqual(self.holds_of(token), 0)


class TestBookingWithHold(HoldTestCase):
	def test_without_a_hold_tickets_others_hold_are_taken(self):
		self.held_by_others(10)

		with self.assertRaises(frappe.ValidationError):
			self.book(1)

	def test_own_hold_books_while_others_hold_the_rest(self):
		self.held_by_others(7)
		token = self.hold(3).hold_token

		self.book(3, token)

		self.assertEqual(self.holds_of(token), 0)
		self.assertEqual(self.ticket_type.remaining_tickets, 0)

	def test_a_lapsed_hold_books_while_tickets_are_free(self):
		token = self.hold(2).hold_token
		frappe.db.set_value("Ticket Hold", {"hold_token": token}, "expires_at", now_datetime())

		self.book(2, token)

		self.assertEqual(self.ticket_type.tickets_sold, 2)

	def test_a_lapsed_hold_fails_once_others_hold_the_tickets(self):
		token = self.hold(2).hold_token
		frappe.db.set_value("Ticket Hold", {"hold_token": token}, "expires_at", now_datetime())
		self.held_by_others(9)

		with self.assertRaises(frappe.ValidationError):
			self.book(2, token)

	def test_a_failed_submit_keeps_the_hold(self):
		token = self.hold(2).hold_token

		with (
			patch(
				"buzz.ticketing.doctype.event_booking.event_booking.EventBooking.generate_tickets",
				side_effect=frappe.ValidationError,
			),
			self.assertRaises(frappe.ValidationError),
		):
			self.book(2, token)
		frappe.db.rollback()

		self.assertEqual(self.holds_of(token), 1)
