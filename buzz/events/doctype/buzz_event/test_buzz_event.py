# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_event.buzz_event import MAX_TOPICS, RESERVED_EVENT_ROUTES
from buzz.tests.factories import BuzzEventFactory, EventTopicFactory, EventVenueFactory


class BuzzEventTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		event = BuzzEventFactory.create()
		cls.event_links = {"team": event.team, "host": event.host, "category": event.category}

	def build_event(self, *traits, **fields):
		return BuzzEventFactory.build(*traits, **self.event_links, **fields)

	def create_event(self, **fields):
		return BuzzEventFactory.create(**self.event_links, **fields)


class TestEventValidation(BuzzEventTestCase):
	def test_refuses_a_tax_rate_above_100(self):
		event = self.build_event(apply_tax=1, tax_percentage=150)
		with self.assertRaises(frappe.ValidationError):
			event.validate_tax_settings()

	def test_refuses_a_negative_tax_rate(self):
		event = self.build_event(apply_tax=1, tax_percentage=-5)
		with self.assertRaises(frappe.ValidationError):
			event.validate_tax_settings()


class TestEventTopics(BuzzEventTestCase):
	def topics(self, count: int) -> list[dict]:
		return [{"topic": EventTopicFactory.create().name} for _ in range(count)]

	def test_saves_up_to_the_topic_limit(self):
		event = self.create_event(topics=self.topics(MAX_TOPICS))
		self.assertEqual(len(event.topics), MAX_TOPICS)

	def test_refuses_more_topics_than_the_limit(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_event(topics=self.topics(MAX_TOPICS + 1))


class TestEventRoute(BuzzEventTestCase):
	def test_reserved_routes_are_rejected(self):
		for route in RESERVED_EVENT_ROUTES:
			with self.subTest(route=route), self.assertRaises(frappe.ValidationError):
				self.create_event(route=route)

	def test_reserved_routes_are_rejected_case_insensitively(self):
		# vue-router matches paths case-insensitively.
		for route in ("Account", "BOOKING-SUCCESS", "Register"):
			with self.subTest(route=route), self.assertRaises(frappe.ValidationError):
				self.create_event(route=route)

	def test_reserved_routes_cover_dashboard_segments(self):
		self.assertIn("booking-success", RESERVED_EVENT_ROUTES)

	def test_manager_section_is_reserved(self):
		self.assertIn("manage", RESERVED_EVENT_ROUTES)

	def test_unreserved_route_is_accepted(self):
		route = f"conference-{frappe.generate_hash(length=6)}"
		self.assertEqual(self.create_event(route=route).route, route)

	def test_new_event_is_published_with_a_title_slug_route(self):
		# None lets the DocType default apply on insert.
		suffix = frappe.generate_hash(length=6)
		event = self.create_event(is_published=None, title=f"Frappe Conf: {suffix}!")
		self.assertTrue(event.is_published)
		self.assertEqual(event.route, f"frappe-conf-{suffix}")

	def test_title_that_slugs_to_a_reserved_route_gets_a_suffix(self):
		self.assertEqual(self.create_event(title="Account").route, "account-event")

	def test_new_event_comes_with_the_default_forms_in_one_save(self):
		# A second save would rewrite the event, which deadlocks two events created at once.
		event = self.create_event()

		creation, modified = frappe.db.get_value("Buzz Event", event.name, ["creation", "modified"])
		self.assertEqual(creation, modified)
		forms = frappe.get_all(
			"Buzz Form", filters={"event": event.name}, fields=["route", "publish"], order_by="route"
		)
		self.assertEqual(
			[form.route for form in forms],
			["enquire-sponsorship", "feedback", "propose-talk", "register", "register-attendee"],
		)
		# Organisers open each page form when they mean to take submissions; registration is
		# always open, it has no page of its own.
		self.assertEqual([form.route for form in forms if form.publish], ["register"])

	def test_same_title_routes_get_a_number_suffix(self):
		title = f"Meetup {frappe.generate_hash(length=6)}"
		first = self.create_event(title=title).route
		self.assertEqual(self.create_event(title=title).route, f"{first}-1")

	def test_explicitly_unpublished_event_stays_a_draft(self):
		self.assertFalse(self.create_event(is_published=0).is_published)


class TestEventLocation(BuzzEventTestCase):
	def test_turning_an_event_online_drops_its_venue(self):
		event = self.build_event("in_person")
		event.medium = "Online"
		event.meeting_link = "https://example.com/room"

		event.clear_unused_location()

		self.assertIsNone(event.venue)
		self.assertEqual(event.meeting_link, "https://example.com/room")

	def test_turning_an_event_in_person_drops_its_meeting_link(self):
		venue = EventVenueFactory.create(team=self.event_links["team"]).name
		event = self.build_event("in_person", venue=venue, meeting_link="https://example.com/room")

		event.clear_unused_location()

		self.assertEqual(event.venue, venue)
		self.assertIsNone(event.meeting_link)

	def test_an_online_event_keeps_a_venue_it_never_had(self):
		event = self.build_event(medium="Online")

		event.clear_unused_location()

		self.assertIsNone(event.venue)


class TestGuestVerificationConfig(BuzzEventTestCase):
	"""`frappe.in_test` is patched off: the check returns early in tests."""

	def test_email_otp_needs_an_outgoing_account(self):
		with (
			patch.object(frappe, "in_test", False),
			patch("buzz.api.booking.guests.email_otp_available", return_value=False),
		):
			self.assertRaises(
				frappe.ValidationError,
				self.event_with_verification("Email OTP").validate_guest_verification_config,
			)

	def test_phone_otp_needs_sms_a_guest_can_be_sent(self):
		with (
			patch.object(frappe, "in_test", False),
			patch("buzz.api.booking.guests.phone_otp_available", return_value=False),
		):
			self.assertRaises(
				frappe.ValidationError,
				self.event_with_verification("Phone OTP").validate_guest_verification_config,
			)

	def test_a_configured_site_passes(self):
		with (
			patch.object(frappe, "in_test", False),
			patch("buzz.api.booking.guests.phone_otp_available", return_value=True),
		):
			self.event_with_verification("Phone OTP").validate_guest_verification_config()

	def test_none_needs_nothing_configured(self):
		with patch.object(frappe, "in_test", False):
			self.event_with_verification("None").validate_guest_verification_config()

	def event_with_verification(self, method: str):
		return self.build_event(allow_guest_booking=1, guest_verification_method=method)
