# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.events.doctype.buzz_event.buzz_event import RESERVED_EVENT_ROUTES
from buzz.tests.factories import BuzzEventFactory, EventVenueFactory

START_DATE = add_days(today(), 30)
END_DATE = add_days(today(), 31)


class BuzzEventTestCase(IntegrationTestCase):
	"""Events share one team, host and category, so each build or create adds no other rows."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		event = BuzzEventFactory.create()
		cls.links = {"team": event.team, "host": event.host, "category": event.category}

	def build_event(self, *traits, **fields):
		return BuzzEventFactory.build(*traits, **self.links, **fields)

	def create_event(self, **fields):
		return BuzzEventFactory.create(**self.links, **fields)


class TestEventValidation(BuzzEventTestCase):
	def test_refuses_a_tax_rate_above_100(self):
		event = self.build_event(apply_tax=1, tax_percentage=150)
		with self.assertRaises(frappe.ValidationError):
			event.validate_tax_settings()

	def test_refuses_a_negative_tax_rate(self):
		event = self.build_event(apply_tax=1, tax_percentage=-5)
		with self.assertRaises(frappe.ValidationError):
			event.validate_tax_settings()

	def test_schedule_start_time_after_event_start_is_valid(self):
		# Regression: times were compared as strings, so "11:00" sorted before "9:00".
		self.event_with_schedule(START_DATE, "11:00:00", "12:00:00").validate_schedule()

	def test_schedule_start_time_before_event_start_is_rejected(self):
		event = self.event_with_schedule(START_DATE, "08:00:00", "08:30:00")
		with self.assertRaises(frappe.ValidationError):
			event.validate_schedule()

	def test_schedule_end_time_after_event_end_is_rejected(self):
		event = self.event_with_schedule(END_DATE, "17:00:00", "19:00:00")
		with self.assertRaises(frappe.ValidationError):
			event.validate_schedule()

	def test_schedule_end_time_before_event_end_is_valid(self):
		self.event_with_schedule(END_DATE, "16:00:00", "16:30:00").validate_schedule()

	def event_with_schedule(self, date: str, start_time: str, end_time: str):
		# Validated directly: an insert would need Event Track rows for the schedule.
		row = {"date": date, "start_time": start_time, "end_time": end_time}
		return self.build_event(
			start_date=START_DATE,
			end_date=END_DATE,
			start_time="9:00:00",
			end_time="18:00:00",
			schedule=[row],
		)


class TestEventRoute(BuzzEventTestCase):
	def test_reserved_routes_are_rejected(self):
		# An event route becomes /b/<route>, so a dashboard segment would shadow it.
		for route in RESERVED_EVENT_ROUTES:
			with self.subTest(route=route), self.assertRaises(frappe.ValidationError):
				self.create_event(route=route)

	def test_reserved_routes_are_rejected_case_insensitively(self):
		# vue-router matches paths case-insensitively, so "Account" is shadowed like "account".
		for route in ("Account", "BOOKING-SUCCESS", "Register"):
			with self.subTest(route=route), self.assertRaises(frappe.ValidationError):
				self.create_event(route=route)

	def test_reserved_routes_cover_dashboard_segments(self):
		# A static route declared ahead of the /:eventRoute/:formRoute catch-all.
		self.assertIn("booking-success", RESERVED_EVENT_ROUTES)

	def test_manager_section_is_reserved(self):
		# /manage ends in a catch-all 404, so an event routed "manage" would lose every custom form.
		self.assertIn("manage", RESERVED_EVENT_ROUTES)

	def test_unreserved_route_is_accepted(self):
		route = f"conference-{frappe.generate_hash(length=6)}"
		self.assertEqual(self.create_event(route=route).route, route)

	def test_new_event_is_published_with_a_hashed_route(self):
		# None lets the DocType default apply on insert.
		event = self.create_event(is_published=None)
		self.assertTrue(event.is_published)
		self.assertRegex(event.route, r"^[0-9a-f]{8}$")

	def test_generated_routes_are_unique(self):
		self.assertNotEqual(self.create_event().route, self.create_event().route)

	def test_explicitly_unpublished_event_stays_a_draft(self):
		self.assertFalse(self.create_event(is_published=0).is_published)


class TestEventLocation(BuzzEventTestCase):
	"""`generate_ics_file` and the booking page read `venue` without consulting `medium`."""

	def test_turning_an_event_online_drops_its_venue(self):
		event = self.build_event("in_person")
		event.medium = "Online"
		event.meeting_link = "https://example.com/room"

		event.clear_unused_location()

		self.assertIsNone(event.venue)
		self.assertEqual(event.meeting_link, "https://example.com/room")

	def test_turning_an_event_in_person_drops_its_meeting_link(self):
		venue = EventVenueFactory.create(team=self.links["team"]).name
		event = self.build_event("in_person", venue=venue, meeting_link="https://example.com/room")

		event.clear_unused_location()

		self.assertEqual(event.venue, venue)
		self.assertIsNone(event.meeting_link)

	def test_an_online_event_keeps_a_venue_it_never_had(self):
		event = self.build_event(medium="Online")

		event.clear_unused_location()

		self.assertIsNone(event.venue)


class TestGuestVerificationConfig(BuzzEventTestCase):
	"""Called directly, with the `frappe.in_test` early return lifted so the checks run."""

	def test_email_otp_needs_an_outgoing_account(self):
		with (
			patch.object(frappe, "in_test", False),
			patch("buzz.api.booking.guests.email_otp_available", return_value=False),
		):
			self.assertRaises(
				frappe.ValidationError, self.event("Email OTP").validate_guest_verification_config
			)

	def test_phone_otp_needs_sms_a_guest_can_be_sent(self):
		with (
			patch.object(frappe, "in_test", False),
			patch("buzz.api.booking.guests.phone_otp_available", return_value=False),
		):
			self.assertRaises(
				frappe.ValidationError, self.event("Phone OTP").validate_guest_verification_config
			)

	def test_a_configured_site_passes(self):
		with (
			patch.object(frappe, "in_test", False),
			patch("buzz.api.booking.guests.phone_otp_available", return_value=True),
		):
			self.event("Phone OTP").validate_guest_verification_config()

	def test_none_needs_nothing_configured(self):
		with patch.object(frappe, "in_test", False):
			self.event("None").validate_guest_verification_config()

	def event(self, method: str):
		return self.build_event(allow_guest_booking=1, guest_verification_method=method)
