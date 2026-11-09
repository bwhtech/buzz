import frappe
from frappe.utils import add_to_date, now_datetime

from buzz.api.booking import hold_tickets, process_booking
from buzz.api.booking.exceptions import RequestAlreadyOpen, RequestNotOpen
from buzz.api.booking.requests import (
	approve_request,
	decline_request,
	get_request_payment_link,
	get_requests,
)
from buzz.api.booking.services import get_booking_access_token
from buzz.api.events.exceptions import CannotManageEvent
from buzz.tests.base_test_cases import BookingTestCase, authorize_payment, make_payment_gateway
from buzz.tests.factories import BuzzEventFactory, EventTicketFactory, EventTicketTypeFactory, UserFactory
from buzz.tests.utils import html_part, mute_outgoing_email
from buzz.ticketing.doctype.ticket_hold.ticket_hold import held_quantities


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

	def request_to_join(self, ticket_type=None) -> str:
		ticket_type = str(ticket_type or self.ticket_type.name)
		with self.set_user(self.booker):
			hold_token = hold_tickets(self.event.name, {ticket_type: 1}).hold_token
			attendees = [{"first_name": "Guest", "email": "guest@example.com", "ticket_type": ticket_type}]
			request = self.booking_request(attendees=attendees, hold_token=hold_token)
			return process_booking(request).booking_name

	def paid_ticket_type(self):
		return EventTicketTypeFactory.create(
			"paid", event=self.event.name, requires_approval=1, max_tickets_available=5
		)

	def booking(self, name: str):
		return frappe.get_doc("Event Booking", name)

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


class TestRegistrationRequests(RequestTestCase):
	def test_free_request_is_confirmed_on_approval(self):
		name = self.request_to_join()

		booking = self.booking(name)
		self.assertEqual((booking.status, booking.docstatus), ("Requested", 0))
		self.assertEqual(self.tickets_of(name), 0)
		self.assertEqual(held_quantities([self.ticket_type.name]), {})
		self.assertIn("No ticket has been issued yet", self.emails_of(name)[0])
		self.assertEqual([row.name for row in get_requests(str(self.event.name))], [name])
		# Desk's plain Submit must not skip the organizer.
		self.assertRaises(frappe.ValidationError, booking.submit)

		approve_request(name)

		booking = self.booking(name)
		self.assertEqual((booking.status, booking.docstatus), ("Confirmed", 1))
		self.assertEqual(self.tickets_of(name), 1)
		self.assertEqual(get_requests(str(self.event.name)), [])

	def test_declined_request_issues_nothing_and_can_be_made_again(self):
		name = self.request_to_join()

		decline_request(name, "The room is full of speakers.")

		booking = self.booking(name)
		self.assertEqual((booking.status, booking.docstatus), ("Rejected", 2))
		self.assertEqual(self.tickets_of(name), 0)
		self.assertIn("The room is full of speakers.", self.emails_of(name)[-1])
		self.assertEqual(self.booking(self.request_to_join()).status, "Requested")

	def test_second_open_request_is_refused(self):
		self.request_to_join()

		self.assertRaises(RequestAlreadyOpen, self.request_to_join)

	def test_only_guest_managers_decide(self):
		name = self.request_to_join()

		with self.set_user(self.outsider):
			self.assertRaises(CannotManageEvent, approve_request, name)
			self.assertRaises(CannotManageEvent, decline_request, name)
			self.assertRaises(CannotManageEvent, get_requests, str(self.event.name))
		self.assertEqual(self.booking(name).status, "Requested")

	def test_event_wide_approval_and_organizer_adds(self):
		self.set_event({"requires_approval": 1})
		plain = EventTicketTypeFactory.create(event=self.event.name)

		self.assertEqual(self.booking(self.request_to_join(plain.name)).status, "Requested")
		# The organizer adds a guest directly.
		booking = process_booking(
			self.booking_request(
				attendees=[{"first_name": "VIP", "email": "vip@example.com", "ticket_type": str(plain.name)}]
			)
		)
		self.assertEqual(self.booking(booking.booking_name).status, "Confirmed")


class TestPaidRegistrationRequests(RequestTestCase):
	def test_paid_request_is_confirmed_once_paid(self):
		ticket_type = self.paid_ticket_type()
		name = self.request_to_join(ticket_type.name)

		approve_request(name)

		booking = self.booking(name)
		self.assertEqual((booking.status, booking.docstatus), ("Payment Pending", 0))
		self.assertEqual(held_quantities([ticket_type.name]), {str(ticket_type.name): 1})
		self.assertIn("Pay now", self.emails_of(name)[-1])
		# The guest may be on the payment page.
		self.assertRaises(RequestNotOpen, decline_request, name)

		authorize_payment(booking)

		self.assertEqual((booking.status, booking.docstatus), ("Confirmed", 1))
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

	def test_lapsed_offer_holds_the_tickets_again(self):
		ticket_type = self.paid_ticket_type()
		name = self.request_to_join(ticket_type.name)
		approve_request(name)

		with self.freeze_time(add_to_date(now_datetime(), hours=49)), self.set_user(self.booker):
			self.assertEqual(held_quantities([ticket_type.name]), {})
			get_request_payment_link(name)
			self.assertEqual(held_quantities([ticket_type.name]), {str(ticket_type.name): 1})


class TestWaitlist(RequestTestCase):
	def test_waitlist_queues_registrations_until_approved(self):
		ticket_type = EventTicketTypeFactory.create(
			event=self.event.name, enable_waitlist=1, max_tickets_available=1
		)
		EventTicketFactory.create("submitted", event=self.event.name, ticket_type=ticket_type.name)

		name = self.request_to_join(ticket_type.name)

		booking = self.booking(name)
		self.assertEqual((booking.status, booking.docstatus), ("Waitlisted", 0))
		self.assertRaises(frappe.ValidationError, booking.submit)
		# Still full: approval fails and the entry stays.
		self.assertRaises(frappe.ValidationError, approve_request, name)
		self.assertEqual(self.booking(name).status, "Waitlisted")

		frappe.db.set_value("Event Ticket Type", ticket_type.name, "max_tickets_available", 2)
		frappe.clear_document_cache("Event Ticket Type", ticket_type.name)
		# The freed spot goes to the queue, not to the next registration.
		self.booker = UserFactory.create_once("waitlist-second@example.com").name
		self.assertEqual(self.booking(self.request_to_join(ticket_type.name)).status, "Waitlisted")

		approve_request(name)

		self.assertEqual(self.booking(name).status, "Confirmed")
		self.assertEqual(self.tickets_of(name), 1)
