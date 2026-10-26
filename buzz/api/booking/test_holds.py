from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime

from buzz.api.booking import get_event_booking_data, hold_tickets, process_booking, release_hold
from buzz.api.booking.exceptions import RegistrationsClosed, TicketsUnavailable, TooManyTicketsHeld
from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzFormFactory,
	EventBookingFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
	OfflinePaymentMethodFactory,
	TicketHoldFactory,
)
from buzz.ticketing.doctype.ticket_hold.ticket_hold import PAYMENT_HOLD_MINUTES, delete_expired_holds
from buzz.utils import build_event_datetimes
from buzz.www.event.registration import RegistrationCard


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
		BuzzFormFactory.set_registration_cutoff(self.event.name, add_to_date(now_datetime(), days=-1))

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


class TestDraftBookingHold(HoldTestCase):
	def setUp(self):
		super().setUp()
		self.set_event({"apply_tax": 0})
		self.ticket_type = EventTicketTypeFactory.create(
			"paid", event=self.event.name, max_tickets_available=10
		)
		self.name = str(self.ticket_type.name)

	def draft(self, quantity: int, **overrides):
		attendees = [
			{"first_name": "Payer", "email": "payer@example.com", "ticket_type": self.name}
		] * quantity
		return EventBookingFactory.create(event=self.event.name, attendees=attendees, **overrides)

	def hold_expiry(self, hold_token: str):
		return frappe.db.get_value("Ticket Hold", {"hold_token": hold_token}, "expires_at")

	def test_a_paid_draft_holds_through_the_payment_window(self):
		start = now_datetime()
		with self.freeze_time(start):
			booking = self.draft(2, hold_token=self.hold(2).hold_token)

		self.assertEqual(
			self.hold_expiry(booking.hold_token), add_to_date(start, minutes=PAYMENT_HOLD_MINUTES)
		)
		self.assertEqual(self.ticket_type.remaining_tickets, 8)

	def test_a_paid_draft_without_a_hold_still_holds(self):
		booking = self.draft(3)

		self.assertTrue(booking.hold_token)
		self.assertEqual(self.ticket_type.remaining_tickets, 7)

	def test_an_offline_draft_holds_until_the_event_ends(self):
		booking = frappe.get_doc("Event Booking", self.book_offline().booking_name)

		_start, event_end = build_event_datetimes(frappe.get_doc("Buzz Event", self.event.name))
		self.assertEqual(self.hold_expiry(booking.hold_token), event_end)

	def test_rejecting_an_offline_draft_releases_its_hold(self):
		booking = frappe.get_doc("Event Booking", self.book_offline().booking_name)

		booking.reject_booking()

		self.assertEqual(self.holds_of(booking.hold_token), 0)

	def test_approving_an_offline_draft_turns_its_hold_into_tickets(self):
		booking = frappe.get_doc("Event Booking", self.book_offline().booking_name)

		booking.approve_booking()

		self.assertEqual(self.holds_of(booking.hold_token), 0)
		self.assertEqual(self.ticket_type.remaining_tickets, 9)

	def test_a_payment_turns_the_hold_into_tickets(self):
		booking = self.draft(2)

		booking.on_payment_authorized("Completed")

		self.assertEqual(self.holds_of(booking.hold_token), 0)
		self.assertEqual(self.ticket_type.remaining_tickets, 8)

	def book_offline(self):
		method = str(OfflinePaymentMethodFactory.create(event=self.event.name).name)
		attendees = [{"first_name": "Offline", "email": "offline@example.com", "ticket_type": self.name}]
		request = self.booking_request(attendees=attendees, is_offline=True, offline_payment_method=method)
		return process_booking(request)


class TestAvailabilityView(HoldTestCase):
	def listed(self, hold_token: str | None = None) -> list[str]:
		data = get_event_booking_data(self.event.route, hold_token)
		return [str(ticket_type.name) for ticket_type in data.available_ticket_types]

	def test_a_ticket_type_held_in_full_is_listed_only_for_its_hold(self):
		token = self.hold(10).hold_token

		self.assertNotIn(self.name, self.listed())
		self.assertIn(self.name, self.listed(token))

	def open_event(self):
		"""A fresh event, so no booking of Administrator's marks it as registered, without the
		default ticket type a new event gets."""
		event = BuzzEventFactory.create()
		BuzzFormFactory.set_registration_cutoff(event.name, None)
		frappe.db.set_value("Event Ticket Type", {"event": event.name}, "is_published", 0)
		return frappe.get_doc("Buzz Event", event.name)

	def test_the_event_page_shows_reserved_while_tickets_are_held(self):
		event = self.open_event()
		ticket_type = EventTicketTypeFactory.create(event=event.name, max_tickets_available=2)

		TicketHoldFactory.create(ticket_type=ticket_type.name, quantity=2)

		self.assertEqual(RegistrationCard(event).as_dict()["state"], "reserved")

	def test_the_event_page_shows_sold_out_when_nothing_is_held(self):
		event = self.open_event()
		ticket_type = EventTicketTypeFactory.create(event=event.name, max_tickets_available=1)
		EventTicketFactory.create("submitted", event=event.name, ticket_type=ticket_type.name)

		self.assertEqual(RegistrationCard(event).as_dict()["state"], "sold-out")


class TestHoldLimits(HoldTestCase):
	def setUp(self):
		super().setUp()
		self.ticket_type = EventTicketTypeFactory.create(event=self.event.name, max_tickets_available=50)
		self.name = str(self.ticket_type.name)
		previous_ip = getattr(frappe.local, "request_ip", None)
		# Unique per test: the hold endpoint commits, so an earlier run's holds outlive rollback.
		frappe.local.request_ip = frappe.generate_hash(length=12)
		self.addCleanup(setattr, frappe.local, "request_ip", previous_ip)

	def test_one_network_holds_at_most_twenty_tickets(self):
		token = self.hold(15).hold_token
		self.hold(20, token)

		with self.assertRaises(TooManyTicketsHeld):
			self.hold(1)

	def test_another_network_still_holds(self):
		self.hold(20)
		frappe.local.request_ip = frappe.generate_hash(length=12)

		self.assertEqual(self.hold(1).remaining, {self.name: 30})


class TestExpiredHoldCleanup(HoldTestCase):
	def test_deletes_expired_holds_only(self):
		expired = TicketHoldFactory.create("expired", ticket_type=self.ticket_type.name)
		live = TicketHoldFactory.create(ticket_type=self.ticket_type.name)

		delete_expired_holds()

		self.assertFalse(frappe.db.exists("Ticket Hold", expired.name))
		self.assertTrue(frappe.db.exists("Ticket Hold", live.name))
