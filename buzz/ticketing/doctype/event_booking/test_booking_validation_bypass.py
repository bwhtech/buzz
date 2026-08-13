# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt
"""Reproduction for the reported access-control / validation-bypass issue.

`Event Booking` grants `create` to the `Buzz User` role, and every User gets that
role on `after_insert` (`buzz.utils.add_buzz_user_role`, wired in `hooks.py`). The
booking eligibility rules — event published, registrations open, add-ons drawn from
the event's catalog, Zoom last names, phone custom fields — live only in
`BookingService` (`buzz/api/booking/services.py`), never in `EventBooking.validate`.

Frappe's generic document API (`/api/resource/Event Booking`,
`frappe.client.insert`) goes straight to `Document.insert()`, so it runs
`EventBooking.validate` and skips every service-level rule. These tests pin both
sides: what the service refuses, and what the same payload achieves when it is
inserted directly by an ordinary logged-in user.
"""

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.booking import process_booking
from buzz.api.booking.exceptions import RegistrationsClosed
from buzz.api.booking.schemas import BookingRequest
from buzz.api.forms.test_forms import ensure_prompt_named_record
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user

ATTACKER = "bypass-attacker@example.com"
VICTIM = "bypass-victim@example.com"


class BypassTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		category = ensure_prompt_named_record("Event Category", "Bypass Category")
		host = ensure_prompt_named_record("Event Host", "Bypass Host")
		owner = create_user("bypass-team-owner@example.com", "Bypass")
		cls.team = create_owned_team(f"Bypass Team {frappe.generate_hash(length=6)}", owner)
		cls.event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": f"Bypass Event {frappe.generate_hash(length=6)}",
				"team": cls.team,
				"start_date": "2030-01-01",
				"end_date": "2030-01-01",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"category": category,
				"host": host,
				"is_published": 1,
			}
		).insert(ignore_permissions=True)
		cls.event.reload()

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event.name)

		self.attacker = create_user(ATTACKER, "Attacker")
		self.victim = create_user(VICTIM, "Victim")
		self.set_event({"is_published": 1, "registrations_close_at": None, "allow_guest_booking": 0})

		self.paid_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event.name,
				"title": f"Bypass Paid {frappe.generate_hash(length=6)}",
				"price": 5000,
				"currency": "INR",
				"is_published": 1,
			}
		).insert(ignore_permissions=True)

	def set_event(self, values):
		frappe.db.set_value("Buzz Event", self.event.name, values)
		frappe.clear_document_cache("Buzz Event", self.event.name)

	def attendee_row(self, **overrides) -> dict:
		row = {
			"first_name": "Poc",
			"last_name": "DirectCreate",
			"email": "closed_test@as.free",
			"ticket_type": str(self.paid_ticket_type.name),
		}
		row.update(overrides)
		return row

	def booking_request(self, **overrides) -> BookingRequest:
		values = {"event": str(self.event.name), "attendees": [self.attendee_row()]}
		values.update(overrides)
		return BookingRequest(**values)

	def insert_as(self, session_user: str, **overrides):
		"""What `/api/resource/Event Booking` and `frappe.client.insert` do: build the
		document from the request payload and insert it under the caller's own
		permissions. No `ignore_permissions`, so the doctype's role permissions decide."""
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


class TestOrdinaryUsersCanWriteBookings(BypassTestCase):
	"""The precondition: the role that lets this happen is granted to everyone."""

	def test_every_new_user_is_granted_the_buzz_user_role(self):
		self.assertIn("Buzz User", frappe.get_roles(self.attacker))

	def test_buzz_user_carries_create_permission_on_event_booking(self):
		self.assertTrue(frappe.has_permission("Event Booking", "create", user=self.attacker))

	def test_buzz_user_cannot_submit(self):
		self.assertFalse(frappe.has_permission("Event Booking", "submit", user=self.attacker))


class TestUnpublishedEventBypass(BypassTestCase):
	def test_service_refuses_an_unpublished_event(self):
		self.set_event({"is_published": 0})
		frappe.set_user(self.attacker)

		with self.assertRaises(frappe.ValidationError):
			process_booking(self.booking_request())

		self.assertIn("Event is not live", frappe.local.message_log[-1]["message"])

	def test_direct_insert_books_an_unpublished_event(self):
		self.set_event({"is_published": 0})

		booking = self.insert_as(self.attacker)

		self.assertTrue(frappe.db.exists("Event Booking", booking.name))
		self.assertEqual(booking.event, self.event.name)
		self.assertFalse(frappe.db.get_value("Buzz Event", self.event.name, "is_published"))


class TestClosedRegistrationsBypass(BypassTestCase):
	def test_service_refuses_once_registrations_have_closed(self):
		self.set_event({"registrations_close_at": "2020-01-01 00:00:00"})
		frappe.set_user(self.attacker)

		with self.assertRaises(RegistrationsClosed):
			process_booking(self.booking_request())

	def test_direct_insert_books_after_registrations_close(self):
		self.set_event({"registrations_close_at": "2020-01-01 00:00:00"})

		booking = self.insert_as(self.attacker)

		self.assertTrue(frappe.db.exists("Event Booking", booking.name))

	def test_direct_insert_books_an_event_that_already_ended(self):
		# No explicit cutoff, so `are_registrations_closed` falls back to the end datetime.
		self.set_event({"start_date": "2020-01-01", "end_date": "2020-01-01"})
		self.addCleanup(self.set_event, {"start_date": "2030-01-01", "end_date": "2030-01-01"})

		booking = self.insert_as(self.attacker)

		self.assertTrue(frappe.db.exists("Event Booking", booking.name))


class TestBookingAttribution(BypassTestCase):
	def test_direct_insert_can_name_another_user_as_the_booker(self):
		"""`user` is a plain Link with no check that it is the session user. The
		`if_owner` restriction keys off `owner`, which Frappe sets itself, so the
		booking lands in the victim's dashboard while the attacker owns the row."""
		booking = self.insert_as(self.attacker, user=self.victim)

		self.assertEqual(booking.user, self.victim)
		self.assertEqual(booking.owner, self.attacker)


class TestWhatValidateStillEnforces(BypassTestCase):
	"""Scope the finding: these rules do live in `EventBooking.validate`, so a direct
	insert does not defeat them."""

	def test_prices_are_refetched_from_the_ticket_type(self):
		booking = self.insert_as(self.attacker, attendees=[self.attendee_row(amount=0)])

		self.assertEqual(booking.attendees[0].amount, 5000)
		self.assertEqual(booking.total_amount, 5000)

	def test_unpublished_ticket_types_are_refused(self):
		frappe.db.set_value("Event Ticket Type", self.paid_ticket_type.name, "is_published", 0)
		frappe.clear_document_cache("Event Ticket Type", self.paid_ticket_type.name)

		with self.assertRaises(frappe.ValidationError):
			self.insert_as(self.attacker)

	def test_a_directly_inserted_booking_stays_a_draft(self):
		booking = self.insert_as(self.attacker)

		self.assertEqual(booking.docstatus, 0)
		self.assertFalse(frappe.db.exists("Event Ticket", {"booking": booking.name}))

	def test_the_attacker_cannot_submit_their_own_booking(self):
		booking = self.insert_as(self.attacker)

		frappe.set_user(self.attacker)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Event Booking", booking.name).submit()


class TestDraftStateIsAttackerControlled(BypassTestCase):
	def test_read_only_status_fields_are_accepted_from_the_payload(self):
		"""`status` and `payment_status` are `read_only`, which Frappe enforces in the
		desk UI only — the REST API writes whatever the payload carries."""
		booking = self.insert_as(self.attacker, status="Confirmed", payment_status="Paid")

		self.assertEqual(booking.status, "Confirmed")
		self.assertEqual(booking.payment_status, "Paid")
