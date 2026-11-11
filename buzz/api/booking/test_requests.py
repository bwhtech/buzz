from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from buzz.api.booking import hold_tickets, process_booking
from buzz.api.booking.exceptions import RequestAlreadyOpen, RequestNotOpen
from buzz.api.booking.requests import (
	approve_request,
	decline_request,
	get_request_counts,
	get_request_payment_link,
	get_requests,
	reopen_request,
	resend_payment_link,
	revoke_request,
)
from buzz.api.booking.services import get_booking_access_token
from buzz.api.comments import get_activity
from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.events.services import events_for
from buzz.api.events.ticket_types import revenue_by_currency
from buzz.tests.base_test_cases import BookingTestCase, authorize_payment, make_payment_gateway
from buzz.tests.factories import BuzzEventFactory, EventTicketFactory, EventTicketTypeFactory, UserFactory
from buzz.tests.utils import html_part, mute_outgoing_email
from buzz.ticketing.doctype.ticket_hold.ticket_hold import held_quantities, live_hold_expiry


class RequestTestCase(BookingTestCase):
	"""A fresh event per test: `process_booking` commits, so requests would pile up on a shared one."""

	def setUp(self):
		self.event = BuzzEventFactory.create(payment_gateways=[{"payment_gateway": make_payment_gateway()}])
		self.event.reload()
		super().setUp()
		mute_outgoing_email(self)
		self.ticket_type = EventTicketTypeFactory.create(
			event=self.event.name, requires_approval=1, max_tickets_available=5
		)

	def request_to_join(self, ticket_type=None, booker: str | None = None) -> str:
		ticket_type = str(ticket_type or self.ticket_type.name)
		with self.set_user(booker or self.booker):
			hold_token = hold_tickets(self.event.name, {ticket_type: 1}).hold_token
			attendees = [{"first_name": "Guest", "email": "guest@example.com", "ticket_type": ticket_type}]
			request = self.booking_request(attendees=attendees, hold_token=hold_token)
			return process_booking(request).booking_name

	def another_booker(self, label: str) -> str:
		return UserFactory.create_once(f"request-{label}@example.com").name

	def paid_ticket_type(self, seats: int = 5):
		return EventTicketTypeFactory.create(
			"paid", event=self.event.name, requires_approval=1, max_tickets_available=seats
		)

	def waitlist_ticket_type(self, *traits, seats: int = 1):
		return EventTicketTypeFactory.create(
			*traits, event=self.event.name, enable_waitlist=1, max_tickets_available=seats
		)

	def sell_out(self, ticket_type, count: int = 1) -> None:
		for _ in range(count):
			EventTicketFactory.create("submitted", event=self.event.name, ticket_type=ticket_type.name)

	def booking(self, name: str):
		return frappe.get_doc("Event Booking", name)

	def state(self, name: str) -> tuple:
		booking = self.booking(name)
		return booking.status, booking.docstatus, booking.request_type

	def tickets_of(self, name: str) -> int:
		return frappe.db.count("Event Ticket", {"booking": name})

	def emails_of(self, name: str) -> list[str]:
		rows = frappe.get_all(
			"Email Queue",
			filters={"reference_doctype": "Event Booking", "reference_name": name},
			pluck="message",
			order_by="creation asc",
		)
		return [html_part(message) for message in rows]

	def rows(self, request_type: str) -> dict:
		return {row.name: row for row in get_requests(str(self.event.name), request_type)}


class TestRegistrationRequests(RequestTestCase):
	def test_free_request_is_confirmed_on_approval(self):
		name = self.request_to_join()

		self.assertEqual(self.state(name), ("Requested", 0, "Approval"))
		self.assertEqual(self.tickets_of(name), 0)
		self.assertEqual(held_quantities([self.ticket_type.name]), {})
		self.assertIn("No ticket has been issued yet", self.emails_of(name)[0])
		# Desk's plain Submit must not skip the organizer.
		self.assertRaises(frappe.ValidationError, self.booking(name).submit)

		approve_request(name)

		self.assertEqual(self.state(name), ("Confirmed", 1, "Approval"))
		self.assertEqual(self.tickets_of(name), 1)
		# A decided request stays on the Approvals page.
		self.assertEqual(self.rows("Approval")[name].status, "Confirmed")

	def test_declined_request_is_kept_and_can_be_reopened(self):
		name = self.request_to_join()

		decline_request(name, "The room is full of speakers.")

		self.assertEqual(self.state(name), ("Rejected", 0, "Approval"))
		self.assertEqual(self.tickets_of(name), 0)
		self.assertIn("The room is full of speakers.", self.emails_of(name)[-1])
		with self.set_user(self.booker):
			self.assertIn(str(self.event.name), {row.name for row in events_for(self.booker)})

		reopen_request(name)

		self.assertEqual(self.state(name), ("Requested", 0, "Approval"))
		approve_request(name)
		self.assertEqual(self.state(name), ("Confirmed", 1, "Approval"))

	def test_declined_guest_can_ask_again_but_not_twice(self):
		name = self.request_to_join()
		decline_request(name)

		second = self.request_to_join()

		self.assertEqual(self.state(second), ("Requested", 0, "Approval"))
		# Reopening the first would give the guest two open requests.
		self.assertRaises(RequestAlreadyOpen, reopen_request, name)
		self.assertEqual(self.state(name), ("Rejected", 0, "Approval"))

	def test_only_declined_requests_reopen(self):
		name = self.request_to_join()

		self.assertRaises(RequestNotOpen, reopen_request, name)
		approve_request(name)
		self.assertRaises(RequestNotOpen, reopen_request, name)
		self.assertRaises(RequestNotOpen, decline_request, name)

	def test_second_open_request_is_refused(self):
		self.request_to_join()

		self.assertRaises(RequestAlreadyOpen, self.request_to_join)

	def test_only_guest_managers_decide(self):
		name = self.request_to_join()
		event = str(self.event.name)

		with self.set_user(self.outsider):
			for call in (
				approve_request,
				decline_request,
				reopen_request,
				revoke_request,
				resend_payment_link,
			):
				self.assertRaises(CannotManageEvent, call, name)
			self.assertRaises(CannotManageEvent, get_requests, event, "Approval")
			self.assertRaises(CannotManageEvent, get_request_counts, event)
		self.assertEqual(self.state(name), ("Requested", 0, "Approval"))

	def test_event_wide_approval_and_organizer_adds(self):
		self.set_event({"requires_approval": 1})
		plain = EventTicketTypeFactory.create(event=self.event.name)

		self.assertEqual(self.state(self.request_to_join(plain.name)), ("Requested", 0, "Approval"))
		# The organizer adds a guest directly.
		booking = process_booking(
			self.booking_request(
				attendees=[{"first_name": "VIP", "email": "vip@example.com", "ticket_type": str(plain.name)}]
			)
		)
		self.assertEqual(self.state(booking.booking_name), ("Confirmed", 1, ""))

	def test_approval_goes_through_after_the_ticket_type_sold_out(self):
		ticket_type = EventTicketTypeFactory.create(
			event=self.event.name, requires_approval=1, max_tickets_available=1
		)
		name = self.request_to_join(ticket_type.name)
		self.sell_out(ticket_type)

		approve_request(name)

		self.assertEqual(self.state(name), ("Confirmed", 1, "Approval"))
		# The override is the organizer's: a new request for the full ticket type is still refused.
		self.assertRaises(
			frappe.ValidationError, self.request_to_join, ticket_type.name, self.another_booker("late")
		)

	def test_requests_are_listed_by_type_and_event(self):
		approval = self.request_to_join()
		waitlisted = self.waitlist_ticket_type()
		self.sell_out(waitlisted)
		entry = self.request_to_join(waitlisted.name, self.another_booker("listed"))
		other_event = BuzzEventFactory.create()

		self.assertEqual(list(self.rows("Approval")), [approval])
		self.assertEqual(list(self.rows("Waitlist")), [entry])
		self.assertEqual(get_requests(str(other_event.name), "Approval"), [])

	def test_decisions_show_in_the_booking_activity(self):
		name = self.request_to_join()

		# Frappe skips version tracking under tests.
		with patch.object(frappe, "in_test", False):
			decline_request(name)
			reopen_request(name)

		changes = [
			(entry.old_value, entry.new_value)
			for entry in get_activity("Event Booking", name)
			if entry.kind == "change"
		]
		self.assertEqual(changes, [("Requested", "Rejected"), ("Rejected", "Requested")])


class TestPaidRegistrationRequests(RequestTestCase):
	def test_paid_request_is_confirmed_once_paid(self):
		ticket_type = self.paid_ticket_type()
		name = self.request_to_join(ticket_type.name)

		approve_request(name)

		self.assertEqual(self.state(name), ("Payment Pending", 0, "Approval"))
		self.assertEqual(held_quantities([ticket_type.name]), {str(ticket_type.name): 1})
		self.assertIn("Pay now", self.emails_of(name)[-1])
		self.assertIsNotNone(self.rows("Approval")[name].offer_expires_at)
		# The guest may be on the payment page.
		self.assertRaises(RequestNotOpen, decline_request, name)
		# Not money yet.
		self.assertEqual(revenue_by_currency(str(self.event.name)), [])

		booking = self.booking(name)
		authorize_payment(booking)

		self.assertEqual(
			(booking.status, booking.docstatus, booking.request_type), ("Confirmed", 1, "Approval")
		)
		self.assertEqual(self.tickets_of(name), 1)
		self.assertEqual(held_quantities([ticket_type.name]), {})

	def test_payment_link_needs_the_booking_token(self):
		ticket_type = self.paid_ticket_type()
		name = self.request_to_join(ticket_type.name)
		token = get_booking_access_token(name)

		with self.set_user("Guest"):
			self.assertRaises(frappe.PermissionError, get_request_payment_link, name, "wrong")
			self.assertRaises(RequestNotOpen, get_request_payment_link, name, token)

		approve_request(name)

		with self.set_user("Guest"):
			self.assertTrue(get_request_payment_link(name, token).payment_link)

	def test_offer_window_follows_the_event_setting(self):
		self.set_event({"payment_offer_hours": "24"})
		ticket_type = self.paid_ticket_type()
		name = self.request_to_join(ticket_type.name)

		approve_request(name)

		expiry = get_datetime(live_hold_expiry(self.booking(name).hold_token))
		hours_left = (expiry - now_datetime()).total_seconds() / 3600
		self.assertAlmostEqual(hours_left, 24, delta=0.1)
		self.assertIn("held for 24 hours", self.emails_of(name)[-1])

	def test_lapsed_offer_reads_as_expired_and_holds_again_when_paying(self):
		ticket_type = self.paid_ticket_type()
		name = self.request_to_join(ticket_type.name)
		approve_request(name)

		with self.freeze_time(add_to_date(now_datetime(), hours=49)):
			self.assertIsNone(self.rows("Approval")[name].offer_expires_at)
			with self.set_user(self.booker):
				get_request_payment_link(name)
			self.assertEqual(held_quantities([ticket_type.name]), {str(ticket_type.name): 1})

	def test_lapsed_offer_is_not_paid_for_once_its_seats_sold(self):
		ticket_type = self.paid_ticket_type(seats=1)
		name = self.request_to_join(ticket_type.name)
		approve_request(name)

		with self.freeze_time(add_to_date(now_datetime(), hours=49)):
			self.sell_out(ticket_type)
			with self.set_user(self.booker):
				self.assertRaises(frappe.ValidationError, get_request_payment_link, name)

	def test_revoke_puts_the_request_back_and_frees_its_seats(self):
		ticket_type = self.paid_ticket_type()
		name = self.request_to_join(ticket_type.name)
		approve_request(name)

		revoke_request(name)

		self.assertEqual(self.state(name), ("Requested", 0, "Approval"))
		self.assertEqual(held_quantities([ticket_type.name]), {})
		with self.set_user(self.booker):
			self.assertRaises(RequestNotOpen, get_request_payment_link, name)
		self.assertRaises(RequestNotOpen, revoke_request, name)

	def test_resend_emails_the_link_again(self):
		ticket_type = self.paid_ticket_type()
		name = self.request_to_join(ticket_type.name)
		self.assertRaises(RequestNotOpen, resend_payment_link, name)
		approve_request(name)
		sent = len(self.emails_of(name))

		resend_payment_link(name)

		self.assertEqual(len(self.emails_of(name)), sent + 1)
		self.assertIn("Pay now", self.emails_of(name)[-1])

	def test_resend_holds_a_lapsed_offer_again_even_when_sold_out(self):
		ticket_type = self.paid_ticket_type(seats=1)
		name = self.request_to_join(ticket_type.name)
		approve_request(name)

		with self.freeze_time(add_to_date(now_datetime(), hours=49)):
			self.sell_out(ticket_type)

			resend_payment_link(name)

			self.assertEqual(held_quantities([ticket_type.name]), {str(ticket_type.name): 1})
			self.assertIsNotNone(self.rows("Approval")[name].offer_expires_at)


class TestWaitlist(RequestTestCase):
	def test_sold_out_ticket_type_queues_registrations(self):
		ticket_type = self.waitlist_ticket_type()
		self.sell_out(ticket_type)

		name = self.request_to_join(ticket_type.name)

		self.assertEqual(self.state(name), ("Waitlisted", 0, "Waitlist"))
		self.assertRaises(frappe.ValidationError, self.booking(name).submit)
		self.assertEqual(self.tickets_of(name), 0)

	def test_let_in_while_sold_out(self):
		ticket_type = self.waitlist_ticket_type()
		self.sell_out(ticket_type)
		name = self.request_to_join(ticket_type.name)

		approve_request(name)

		self.assertEqual(self.state(name), ("Confirmed", 1, "Waitlist"))
		self.assertEqual(self.tickets_of(name), 1)
		# Still oversold: the next registration queues instead of booking.
		late = self.request_to_join(ticket_type.name, self.another_booker("after-let-in"))
		self.assertEqual(self.state(late), ("Waitlisted", 0, "Waitlist"))

	def test_paid_let_in_while_sold_out_holds_the_seat(self):
		ticket_type = self.waitlist_ticket_type("paid")
		self.sell_out(ticket_type)
		name = self.request_to_join(ticket_type.name)

		approve_request(name)

		self.assertEqual(self.state(name), ("Payment Pending", 0, "Waitlist"))
		self.assertEqual(held_quantities([ticket_type.name]), {str(ticket_type.name): 1})
		booking = self.booking(name)
		authorize_payment(booking)
		self.assertEqual((booking.status, booking.docstatus), ("Confirmed", 1))

	def test_freed_seat_goes_to_the_queue(self):
		ticket_type = self.waitlist_ticket_type()
		self.sell_out(ticket_type)
		first = self.request_to_join(ticket_type.name)

		frappe.db.set_value("Event Ticket Type", ticket_type.name, "max_tickets_available", 2)
		frappe.clear_document_cache("Event Ticket Type", ticket_type.name)

		second = self.request_to_join(ticket_type.name, self.another_booker("second"))
		self.assertEqual(self.state(second), ("Waitlisted", 0, "Waitlist"))
		counts = get_request_counts(str(self.event.name))
		self.assertEqual((counts.waiting, counts.seats_free), (2, {ticket_type.title: 1}))
		approve_request(first)
		self.assertEqual(self.state(first), ("Confirmed", 1, "Waitlist"))

	def test_positions_count_waiting_entries_per_ticket_type(self):
		general = self.waitlist_ticket_type()
		student = self.waitlist_ticket_type()
		self.sell_out(general)
		self.sell_out(student)
		first = self.request_to_join(general.name, self.another_booker("pos-1"))
		second = self.request_to_join(general.name, self.another_booker("pos-2"))
		third = self.request_to_join(general.name, self.another_booker("pos-3"))
		other = self.request_to_join(student.name, self.another_booker("pos-4"))

		approve_request(first)

		rows = self.rows("Waitlist")
		self.assertEqual([rows[name].position for name in (first, second, third, other)], [None, 1, 2, 1])

	def test_counts(self):
		self.request_to_join()
		ticket_type = self.waitlist_ticket_type()
		self.sell_out(ticket_type)
		self.request_to_join(ticket_type.name, self.another_booker("count"))

		counts = get_request_counts(str(self.event.name))

		self.assertEqual((counts.pending, counts.waiting, counts.seats_free), (1, 1, {ticket_type.title: 0}))

	def test_removed_and_revoked_entries_go_back_to_the_waitlist(self):
		ticket_type = self.waitlist_ticket_type("paid")
		self.sell_out(ticket_type)
		name = self.request_to_join(ticket_type.name)

		decline_request(name)
		self.assertEqual(self.state(name), ("Rejected", 0, "Waitlist"))
		reopen_request(name)
		self.assertEqual(self.state(name), ("Waitlisted", 0, "Waitlist"))

		approve_request(name)
		revoke_request(name)

		self.assertEqual(self.state(name), ("Waitlisted", 0, "Waitlist"))
		self.assertEqual(held_quantities([ticket_type.name]), {})
