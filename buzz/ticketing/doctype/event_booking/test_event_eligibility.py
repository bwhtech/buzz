# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt
"""Who may create an Event Booking, and for which events.

Eligibility (event published, registrations open) used to live only in
`BookingService`, so the generic document API reached `Document.insert()`
without it. These pin both halves of the fix: ordinary users cannot write
bookings at all, and the ones who can are held to their own team's events.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime, today

from buzz.api.booking import process_booking
from buzz.api.booking.exceptions import RegistrationsClosed
from buzz.api.booking.schemas import BookingRequest
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	UserFactory,
)

ATTENDEE = "eligibility-attendee@example.com"
ORGANISER = "eligibility-organiser@example.com"
OUTSIDER = "eligibility-outsider@example.com"


class EligibilityTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		owner = UserFactory.create_once("eligibility-team-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(owner).name
		cls.event = BuzzEventFactory.create(team=cls.team)
		cls.event.reload()
		cls.attendee = UserFactory.create_once(ATTENDEE).name
		cls.organiser = UserFactory.create_once(ORGANISER).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.organiser, team_role="Manager")
		# An Event Manager by role, but on a team that does not own `cls.event`.
		cls.outsider = UserFactory.create_once(OUTSIDER).name
		BuzzTeamFactory.create_owned_by(cls.outsider)

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))
		frappe.clear_messages()
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event.name)
		self.set_event({"is_published": 1, "registrations_close_at": None, "allow_guest_booking": 0})
		self.paid_ticket_type = self.create_ticket_type(price=5000)

	def create_ticket_type(self, price: float):
		return EventTicketTypeFactory.create(
			event=self.event.name, prices=[{"currency": "INR", "price": price}]
		)

	def set_event(self, values):
		frappe.db.set_value("Buzz Event", self.event.name, values)
		frappe.clear_document_cache("Buzz Event", self.event.name)

	def close_registrations(self):
		self.set_event({"registrations_close_at": add_days(now_datetime(), -1)})

	def attendee_row(self, **overrides) -> dict:
		row = {
			"first_name": "Test",
			"last_name": "Attendee",
			"email": ATTENDEE,
			"ticket_type": str(self.paid_ticket_type.name),
		}
		row.update(overrides)
		return row

	def booking_request(self, **overrides) -> BookingRequest:
		values = {"event": str(self.event.name), "attendees": [self.attendee_row()]}
		values.update(overrides)
		return BookingRequest(**values)

	def insert_as(self, session_user: str, **overrides):
		"""Insert under the caller's own permissions, like the generic document API:
		no `ignore_permissions`, so role permissions and `validate` decide."""
		values = {"user": session_user, "currency": "INR", "attendees": [self.attendee_row()], **overrides}
		with self.set_user(session_user):
			return EventBookingFactory.create(event=str(self.event.name), **values)


class TestOrdinaryUsersCannotWriteBookings(EligibilityTestCase):
	"""Bookings are only ever written by the service flow, which runs with
	`ignore_permissions`. Nothing user-facing needs create or write."""

	def test_every_new_user_is_granted_the_buzz_user_role(self):
		self.assertIn("Buzz User", frappe.get_roles(self.attendee))

	def test_buzz_user_can_read_bookings(self):
		self.assertTrue(frappe.has_permission("Event Booking", "read", user=self.attendee))

	def test_buzz_user_cannot_create(self):
		self.assertFalse(frappe.has_permission("Event Booking", "create", user=self.attendee))

	def test_buzz_user_cannot_write(self):
		self.assertFalse(frappe.has_permission("Event Booking", "write", user=self.attendee))

	def test_buzz_user_cannot_submit(self):
		self.assertFalse(frappe.has_permission("Event Booking", "submit", user=self.attendee))

	def test_a_direct_insert_by_a_buzz_user_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self.insert_as(self.attendee)


class TestEventManagersAreHeldToTheirOwnTeam(EligibilityTestCase):
	"""`Event Manager` is granted by membership of any team, so the role alone must
	not open another team's events."""

	def test_an_outsider_may_not_book_an_unpublished_event(self):
		self.set_event({"is_published": 0})

		with self.assertRaises(frappe.ValidationError):
			self.insert_as(self.outsider)

		self.assertIn("Event Manager", frappe.get_roles(self.outsider))

	def test_an_outsider_may_not_book_after_registrations_close(self):
		self.close_registrations()

		with self.assertRaises(RegistrationsClosed):
			self.insert_as(self.outsider)

	def test_an_outsider_may_not_book_an_event_that_already_ended(self):
		# No explicit cutoff, so `are_registrations_closed` falls back to the end datetime.
		self.addCleanup(
			self.set_event, {"start_date": self.event.start_date, "end_date": self.event.end_date}
		)
		self.set_event({"start_date": add_days(today(), -10), "end_date": add_days(today(), -10)})

		with self.assertRaises(RegistrationsClosed):
			self.insert_as(self.outsider)

	def test_an_outsider_may_book_an_open_published_event(self):
		booking = self.insert_as(self.outsider)

		self.assertTrue(frappe.db.exists("Event Booking", booking.name))


class TestTheServiceFlowRefusesIneligibleEvents(EligibilityTestCase):
	def test_service_refuses_an_unpublished_event(self):
		self.set_event({"is_published": 0})

		with self.set_user(self.attendee), self.assertRaises(frappe.ValidationError):
			process_booking(self.booking_request())

		self.assertIn("Event is not live", frappe.local.message_log[-1]["message"])

	def test_service_refuses_once_registrations_have_closed(self):
		self.close_registrations()

		with self.set_user(self.attendee), self.assertRaises(RegistrationsClosed):
			process_booking(self.booking_request())


class TestLegitimateFlowsStillWork(EligibilityTestCase):
	def test_the_guard_does_not_apply_to_the_vetted_service_flow(self):
		# Free ticket keeps the flow off the payment gateway.
		free_ticket_type = str(self.create_ticket_type(price=0).name)
		request = self.booking_request(attendees=[self.attendee_row(ticket_type=free_ticket_type)])

		with self.set_user(self.attendee):
			payload = process_booking(request)

		self.assertTrue(frappe.db.exists("Event Booking", payload.booking_name))

	def test_an_event_organiser_may_book_their_own_closed_event(self):
		# Organisers are exempt (comp tickets, pre-launch testing).
		self.set_event({"is_published": 0})
		self.close_registrations()

		booking = self.insert_as(self.organiser)

		self.assertTrue(frappe.db.exists("Event Booking", booking.name))

	def test_a_draft_booked_while_open_survives_registrations_closing(self):
		# A trusted flow (payment authorisation, offline approval) must still write a
		# draft made while open, or a paid booking is stranded.
		booking = self.insert_as(self.organiser)
		self.close_registrations()

		booking.reload()
		booking.flags.ignore_permissions = True
		booking.save()  # must not raise

		self.assertTrue(frappe.db.exists("Event Booking", booking.name))


class TestTheGuardCannotBeSteppedAround(EligibilityTestCase):
	"""The guard runs on every write, so a draft cannot outlive its event's
	eligibility by being edited or repointed after the fact."""

	def test_an_outsider_cannot_grow_a_draft_after_registrations_close(self):
		free_type = str(self.create_ticket_type(price=0).name)
		booking = self.insert_as(self.outsider, attendees=[self.attendee_row(ticket_type=free_type)])
		self.close_registrations()

		with self.set_user(self.outsider):
			booking.reload()
			booking.append(
				"attendees", self.attendee_row(email="smuggled@example.com", ticket_type=free_type)
			)
			with self.assertRaises(RegistrationsClosed):
				booking.save()

		self.assertEqual(frappe.db.count("Event Booking Attendee", {"parent": booking.name}), 1)

	def test_a_draft_cannot_be_repointed_at_a_closed_event(self):
		# Ticket types pin a draft to its event, so it cannot reach a closed one afterwards.
		booking = self.insert_as(self.organiser)
		closed_event = BuzzEventFactory.create(
			team=self.team, registrations_close_at=add_days(now_datetime(), -1)
		)

		with self.set_user(self.organiser), self.assertRaises(frappe.ValidationError):
			booking.event = closed_event.name
			booking.save()

		self.assertEqual(frappe.db.get_value("Event Booking", booking.name, "event"), str(self.event.name))


class TestWhatValidateAlreadyEnforced(EligibilityTestCase):
	"""Rules that predate the eligibility guard, kept as guardrails."""

	def test_prices_are_refetched_from_the_ticket_type(self):
		booking = self.insert_as(self.organiser, attendees=[self.attendee_row(amount=0)])

		self.assertEqual(booking.attendees[0].amount, 5000)
		self.assertEqual(booking.total_amount, 5000)

	def test_unpublished_ticket_types_are_refused(self):
		frappe.db.set_value("Event Ticket Type", self.paid_ticket_type.name, "is_published", 0)
		frappe.clear_document_cache("Event Ticket Type", self.paid_ticket_type.name)

		with self.assertRaises(frappe.ValidationError):
			self.insert_as(self.organiser)
