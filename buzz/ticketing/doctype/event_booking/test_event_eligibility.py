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

from buzz.api.booking import process_booking
from buzz.api.booking.exceptions import RegistrationsClosed
from buzz.api.booking.schemas import BookingRequest
from buzz.api.forms.test_forms import ensure_prompt_named_record
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.events.doctype.buzz_team_membership.buzz_team_membership import upsert_membership

ATTENDEE = "eligibility-attendee@example.com"
ORGANISER = "eligibility-organiser@example.com"
OUTSIDER = "eligibility-outsider@example.com"


class EligibilityTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Eligibility Category")
		cls.host = ensure_prompt_named_record("Event Host", "Eligibility Host")
		owner = create_user("eligibility-team-owner@example.com", "Eligibility")
		cls.team = create_owned_team(f"Eligibility Team {frappe.generate_hash(length=6)}", owner)
		cls.event = cls.make_event()
		cls.event.reload()

	@classmethod
	def make_event(cls, **overrides):
		values = {
			"doctype": "Buzz Event",
			"title": f"Eligibility Event {frappe.generate_hash(length=6)}",
			"team": cls.team,
			"start_date": "2030-01-01",
			"end_date": "2030-01-01",
			"start_time": "10:00:00",
			"end_time": "18:00:00",
			"medium": "Online",
			"category": cls.category,
			"host": cls.host,
			"is_published": 1,
		}
		values.update(overrides)
		return frappe.get_doc(values).insert(ignore_permissions=True)

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event.name)

		self.attendee = create_user(ATTENDEE, "Attendee")
		self.organiser = create_user(ORGANISER, "Organiser")
		upsert_membership(self.team, self.organiser, "Manager")
		self.set_event({"is_published": 1, "registrations_close_at": None, "allow_guest_booking": 0})

		self.paid_ticket_type = self.make_ticket_type(price=5000)

	def make_ticket_type(self, event=None, price=0):
		return frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": event or self.event.name,
				"title": f"Eligibility {frappe.generate_hash(length=6)}",
				"price": price,
				"currency": "INR",
				"is_published": 1,
			}
		).insert(ignore_permissions=True)

	def outsider_managing_another_team(self) -> str:
		"""An Event Manager by role, but on a team that does not own `self.event`."""
		outsider = create_user(OUTSIDER, "Outsider")
		other_team = create_owned_team(f"Eligibility Other {frappe.generate_hash(length=6)}", outsider)
		upsert_membership(other_team, outsider, "Manager")
		return outsider

	def set_event(self, values):
		frappe.db.set_value("Buzz Event", self.event.name, values)
		frappe.clear_document_cache("Buzz Event", self.event.name)

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
		"""Insert under the caller's own permissions, like the generic document API —
		no `ignore_permissions`, so role permissions and `validate` decide."""
		payload = {
			"doctype": "Event Booking",
			"event": str(self.event.name),
			"user": session_user,
			"currency": "INR",
			"attendees": [self.attendee_row()],
		}
		payload.update(overrides)

		frappe.set_user(session_user)
		try:
			return frappe.get_doc(payload).insert()
		finally:
			frappe.set_user("Administrator")


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
		outsider = self.outsider_managing_another_team()
		self.set_event({"is_published": 0})

		with self.assertRaises(frappe.ValidationError):
			self.insert_as(outsider, user=outsider)

		self.assertIn("Event Manager", frappe.get_roles(outsider))

	def test_an_outsider_may_not_book_after_registrations_close(self):
		outsider = self.outsider_managing_another_team()
		self.set_event({"registrations_close_at": "2020-01-01 00:00:00"})

		with self.assertRaises(RegistrationsClosed):
			self.insert_as(outsider, user=outsider)

	def test_an_outsider_may_not_book_an_event_that_already_ended(self):
		# No explicit cutoff, so `are_registrations_closed` falls back to the end datetime.
		outsider = self.outsider_managing_another_team()
		self.set_event({"start_date": "2020-01-01", "end_date": "2020-01-01"})
		self.addCleanup(self.set_event, {"start_date": "2030-01-01", "end_date": "2030-01-01"})

		with self.assertRaises(RegistrationsClosed):
			self.insert_as(outsider, user=outsider)

	def test_an_outsider_may_book_an_open_published_event(self):
		outsider = self.outsider_managing_another_team()

		booking = self.insert_as(outsider, user=outsider)

		self.assertTrue(frappe.db.exists("Event Booking", booking.name))


class TestTheServiceFlowRefusesIneligibleEvents(EligibilityTestCase):
	def test_service_refuses_an_unpublished_event(self):
		self.set_event({"is_published": 0})
		frappe.set_user(self.attendee)

		with self.assertRaises(frappe.ValidationError):
			process_booking(self.booking_request())

		self.assertIn("Event is not live", frappe.local.message_log[-1]["message"])

	def test_service_refuses_once_registrations_have_closed(self):
		self.set_event({"registrations_close_at": "2020-01-01 00:00:00"})
		frappe.set_user(self.attendee)

		with self.assertRaises(RegistrationsClosed):
			process_booking(self.booking_request())


class TestLegitimateFlowsStillWork(EligibilityTestCase):
	def test_the_guard_does_not_apply_to_the_vetted_service_flow(self):
		# Free ticket keeps the flow off the payment gateway.
		free_ticket_type = self.make_ticket_type(price=0)

		frappe.set_user(self.attendee)
		payload = process_booking(
			self.booking_request(attendees=[self.attendee_row(ticket_type=str(free_ticket_type.name))])
		).__json__()

		self.assertIn("booking_name", payload)
		self.assertTrue(frappe.db.exists("Event Booking", payload["booking_name"]))

	def test_an_event_organiser_may_book_their_own_closed_event(self):
		# Organisers are exempt (comp tickets, pre-launch testing).
		self.set_event({"is_published": 0, "registrations_close_at": "2020-01-01 00:00:00"})

		booking = self.insert_as(self.organiser, user=self.organiser)

		self.assertTrue(frappe.db.exists("Event Booking", booking.name))

	def test_a_draft_booked_while_open_survives_registrations_closing(self):
		# A draft made while open must stay writable via a trusted flow (payment
		# authorisation, offline approval) after close, or a paid booking is stranded.
		booking = self.insert_as(self.organiser, user=self.organiser)
		self.set_event({"registrations_close_at": "2020-01-01 00:00:00"})

		booking.reload()
		booking.flags.ignore_permissions = True
		booking.save()  # must not raise

		self.assertTrue(frappe.db.exists("Event Booking", booking.name))


class TestTheGuardCannotBeSteppedAround(EligibilityTestCase):
	"""The guard runs on every write, so a draft cannot outlive its event's
	eligibility by being edited or repointed after the fact."""

	def test_an_outsider_cannot_grow_a_draft_after_registrations_close(self):
		free_type = self.make_ticket_type(price=0)
		outsider = self.outsider_managing_another_team()
		booking = self.insert_as(
			outsider,
			user=outsider,
			attendees=[self.attendee_row(ticket_type=str(free_type.name))],
		)
		self.set_event({"registrations_close_at": "2020-01-01 00:00:00"})

		frappe.set_user(outsider)
		booking.reload()
		booking.append(
			"attendees",
			self.attendee_row(email="smuggled@example.com", ticket_type=str(free_type.name)),
		)

		with self.assertRaises(RegistrationsClosed):
			booking.save()

		self.assertEqual(frappe.db.count("Event Booking Attendee", {"parent": booking.name}), 1)

	def test_a_draft_cannot_be_repointed_at_a_closed_event(self):
		# The guard only runs on creation, so a draft must not be able to reach a
		# closed event afterwards. Ticket types are what pin it down.
		booking = self.insert_as(self.organiser, user=self.organiser)
		closed_event = self.make_event(registrations_close_at="2020-01-01 00:00:00")

		frappe.set_user(self.organiser)
		booking.event = closed_event.name
		with self.assertRaises(frappe.ValidationError):
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
