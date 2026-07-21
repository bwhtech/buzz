# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from buzz.api import are_registrations_closed
from buzz.events.doctype.buzz_event.buzz_event import RESERVED_EVENT_ROUTES, create_from_template
from buzz.events.doctype.event_template.event_template import create_template_from_event


class TestBuzzEvent(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.create_test_fixtures()

	@classmethod
	def create_test_fixtures(cls):
		if not frappe.db.exists("Event Category", "Test Category"):
			frappe.get_doc({"doctype": "Event Category", "category_name": "Test Category"}).insert(
				ignore_permissions=True
			)

		if not frappe.db.exists("Event Host", "Test Host"):
			frappe.get_doc({"doctype": "Event Host", "host_name": "Test Host"}).insert(
				ignore_permissions=True
			)

	def tearDown(self):
		frappe.db.rollback()

	# ==================== Schedule Validation Tests ====================

	def _make_event_with_schedule(self, schedule_overrides, **event_overrides):
		"""Helper to create a Buzz Event with a single schedule item for validation tests."""
		event_defaults = {
			"doctype": "Buzz Event",
			"title": "Schedule Test Event",
			"category": "Test Category",
			"host": "Test Host",
			"start_date": "2026-03-05",
			"end_date": "2026-03-06",
			"start_time": "9:00:00",
			"end_time": "18:00:00",
		}
		event_defaults.update(event_overrides)
		event = frappe.get_doc(event_defaults)

		# Directly call validate_schedule instead of insert to avoid
		# needing linked Event Track records in the test database
		for row in schedule_overrides:
			event.append("schedule", row)
		return event

	def test_schedule_start_time_after_event_start_is_valid(self):
		"""Schedule at 11:00 should be valid when event starts at 9:00 (regression: string comparison bug)"""
		event = self._make_event_with_schedule(
			[{"date": "2026-03-05", "start_time": "11:00:00", "end_time": "12:00:00"}]
		)
		# Should not raise
		event.validate_schedule()

	def test_schedule_start_time_before_event_start_is_rejected(self):
		"""Schedule at 08:00 should be rejected when event starts at 9:00"""
		event = self._make_event_with_schedule(
			[{"date": "2026-03-05", "start_time": "08:00:00", "end_time": "08:30:00"}]
		)
		with self.assertRaises(frappe.exceptions.ValidationError):
			event.validate_schedule()

	def test_schedule_end_time_after_event_end_is_rejected(self):
		"""Schedule ending at 19:00 should be rejected when event ends at 18:00"""
		event = self._make_event_with_schedule(
			[{"date": "2026-03-06", "start_time": "17:00:00", "end_time": "19:00:00"}]
		)
		with self.assertRaises(frappe.exceptions.ValidationError):
			event.validate_schedule()

	def test_schedule_end_time_before_event_end_is_valid(self):
		"""Schedule ending at 16:30 should be valid when event ends at 18:00"""
		event = self._make_event_with_schedule(
			[{"date": "2026-03-06", "start_time": "16:00:00", "end_time": "16:30:00"}]
		)
		# Should not raise
		event.validate_schedule()

	# ==================== Reserved Route Tests ====================

	def _make_event_with_route(self, route):
		return frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": f"Route Test Event {route}",
				"category": "Test Category",
				"host": "Test Host",
				"start_date": frappe.utils.today(),
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"route": route,
			}
		)

	def test_reserved_routes_are_rejected(self):
		"""Every reserved segment must be refused as an event route.

		An event route becomes /b/<route>, so any route matching a top-level
		dashboard segment would be shadowed by that segment's own page.
		"""
		for route in RESERVED_EVENT_ROUTES:
			with self.subTest(route=route):
				with self.assertRaises(frappe.exceptions.ValidationError):
					self._make_event_with_route(route).insert()
				frappe.db.rollback()

	def test_reserved_routes_are_rejected_case_insensitively(self):
		"""Mixed-case spellings of a reserved segment must be refused too.

		vue-router matches paths case-insensitively, so an event routed
		"Account" is shadowed by /b/account exactly as "account" would be.
		"""
		for route in ("Account", "BOOKING-SUCCESS", "Register"):
			with self.subTest(route=route):
				with self.assertRaises(frappe.exceptions.ValidationError):
					self._make_event_with_route(route).insert()
				frappe.db.rollback()

	def test_reserved_routes_cover_dashboard_segments(self):
		"""booking-success is reserved: it is a static route declared ahead of the
		/:eventRoute/:formRoute catch-all, so an event using it would have every
		custom form swallowed by the booking confirmation page.
		"""
		self.assertIn("booking-success", RESERVED_EVENT_ROUTES)

	def test_unreserved_route_is_accepted(self):
		"""A route that shadows nothing saves normally."""
		event = self._make_event_with_route("my-conference-2026")
		event.insert()
		self.assertEqual(event.route, "my-conference-2026")

	# ==================== Create from Template Tests ====================

	def test_create_from_template_copies_direct_fields(self):
		"""Test that direct fields are copied from template to event"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Direct Fields Template",
				"category": "Test Category",
				"host": "Test Host",
				"medium": "Online",
				"about": "About text",
				"short_description": "Short desc",
				"time_zone": "Asia/Kolkata",
				"allow_guest_booking": 1,
				"guest_verification_method": "Email OTP",
				"send_ticket_email": 1,
				"apply_tax": 1,
				"tax_label": "GST",
				"tax_percentage": 18,
			}
		)
		template.insert()

		options = {
			"category": 1,
			"host": 1,
			"medium": 1,
			"about": 1,
			"short_description": 1,
			"time_zone": 1,
			"allow_guest_booking": 1,
			"guest_verification_method": 1,
			"send_ticket_email": 1,
			"apply_tax": 1,
			"tax_label": 1,
			"tax_percentage": 1,
		}

		event_name = create_from_template(template.name, frappe.as_json(options))
		event = frappe.get_doc("Buzz Event", event_name)

		self.assertEqual(event.category, "Test Category")
		self.assertEqual(event.host, "Test Host")
		self.assertEqual(event.medium, "Online")
		self.assertEqual(event.about, "About text")
		self.assertEqual(event.short_description, "Short desc")
		self.assertEqual(event.time_zone, "Asia/Kolkata")
		self.assertEqual(event.allow_guest_booking, 1)
		self.assertEqual(event.guest_verification_method, "Email OTP")
		self.assertEqual(event.send_ticket_email, 1)
		self.assertEqual(event.apply_tax, 1)
		self.assertEqual(event.tax_label, "GST")
		self.assertEqual(event.tax_percentage, 18)

	def test_create_from_template_respects_unselected_options(self):
		"""Test that unselected options are not copied"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Selective Template",
				"category": "Test Category",
				"host": "Test Host",
				"medium": "In Person",
				"about": "Should not appear",
				"apply_tax": 1,
				"tax_percentage": 18,
			}
		)
		template.insert()

		options = {"category": 1, "host": 1, "medium": 0, "about": 0, "apply_tax": 0}

		event_name = create_from_template(template.name, frappe.as_json(options))
		event = frappe.get_doc("Buzz Event", event_name)

		self.assertEqual(event.category, "Test Category")
		self.assertEqual(event.host, "Test Host")
		self.assertFalse(event.about)
		self.assertFalse(event.apply_tax)

	def test_create_from_template_additional_fields_override(self):
		"""Test that additional_fields override template values"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Override Template",
				"category": "Test Category",
				"host": "Test Host",
			}
		)
		template.insert()

		# Don't copy category from template, provide via additional_fields
		options = {"host": 1}
		additional_fields = {"category": "Test Category"}

		event_name = create_from_template(
			template.name, frappe.as_json(options), frappe.as_json(additional_fields)
		)
		event = frappe.get_doc("Buzz Event", event_name)

		self.assertEqual(event.category, "Test Category")
		self.assertEqual(event.host, "Test Host")

	def test_create_from_template_creates_ticket_types(self):
		"""Test that ticket types are created as linked documents"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Ticket Template",
				"category": "Test Category",
				"host": "Test Host",
				"template_ticket_types": [
					{
						"title": "Early Bird",
						"price": 500,
						"currency": "INR",
						"is_published": 1,
						"max_tickets_available": 100,
					},
					{"title": "Regular", "price": 1000, "currency": "INR", "is_published": 1},
				],
			}
		)
		template.insert()

		options = {"category": 1, "host": 1, "ticket_types": 1}
		event_name = create_from_template(template.name, frappe.as_json(options))

		ticket_types = frappe.get_all(
			"Event Ticket Type",
			filters={"event": event_name, "title": ["in", ["Early Bird", "Regular"]]},
			fields=["title", "price", "max_tickets_available"],
			order_by="price",
		)
		self.assertEqual(len(ticket_types), 2)
		self.assertEqual(ticket_types[0].title, "Early Bird")
		self.assertEqual(ticket_types[0].price, 500)
		self.assertEqual(ticket_types[0].max_tickets_available, 100)
		self.assertEqual(ticket_types[1].title, "Regular")
		self.assertEqual(ticket_types[1].price, 1000)

	def test_create_from_template_creates_add_ons(self):
		"""Test that add-ons are created as linked documents"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "AddOn Template",
				"category": "Test Category",
				"host": "Test Host",
				"template_add_ons": [
					{
						"title": "Workshop Access",
						"price": 2000,
						"currency": "INR",
						"enabled": 1,
						"user_selects_option": 1,
						"options": "Morning\nAfternoon",
					}
				],
			}
		)
		template.insert()

		options = {"category": 1, "host": 1, "add_ons": 1}
		event_name = create_from_template(template.name, frappe.as_json(options))

		add_ons = frappe.get_all(
			"Ticket Add-on",
			filters={"event": event_name},
			fields=["title", "price", "user_selects_option", "options"],
		)
		self.assertEqual(len(add_ons), 1)
		self.assertEqual(add_ons[0].title, "Workshop Access")
		self.assertEqual(add_ons[0].price, 2000)
		self.assertEqual(add_ons[0].user_selects_option, 1)
		self.assertEqual(add_ons[0].options, "Morning\nAfternoon")

	def test_create_from_template_creates_custom_fields(self):
		"""Test that custom fields are created as linked documents"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "CustomField Template",
				"category": "Test Category",
				"host": "Test Host",
				"template_custom_fields": [
					{
						"label": "Company",
						"fieldname": "company",
						"fieldtype": "Data",
						"applied_to": "Booking",
						"mandatory": 1,
						"enabled": 1,
						"placeholder": "Enter company name",
					}
				],
			}
		)
		template.insert()

		options = {"category": 1, "host": 1, "custom_fields": 1}
		event_name = create_from_template(template.name, frappe.as_json(options))

		custom_fields = frappe.get_all(
			"Buzz Custom Field",
			filters={"event": event_name},
			fields=["label", "fieldtype", "mandatory", "placeholder"],
		)
		self.assertEqual(len(custom_fields), 1)
		self.assertEqual(custom_fields[0].label, "Company")
		self.assertEqual(custom_fields[0].fieldtype, "Data")
		self.assertEqual(custom_fields[0].mandatory, 1)
		self.assertEqual(custom_fields[0].placeholder, "Enter company name")

	def test_create_from_template_skips_linked_docs_when_unselected(self):
		"""Test that linked docs are not created when options are 0"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Skip Linked Template",
				"category": "Test Category",
				"host": "Test Host",
				"template_ticket_types": [
					{"title": "Skipped", "price": 100, "currency": "INR", "is_published": 1}
				],
				"template_add_ons": [
					{"title": "Skipped Addon", "price": 50, "currency": "INR", "enabled": 1}
				],
				"template_custom_fields": [
					{
						"label": "Skipped Field",
						"fieldname": "skipped",
						"fieldtype": "Data",
						"applied_to": "Booking",
						"enabled": 1,
					}
				],
			}
		)
		template.insert()

		options = {"category": 1, "host": 1, "ticket_types": 0, "add_ons": 0, "custom_fields": 0}
		event_name = create_from_template(template.name, frappe.as_json(options))

		self.assertEqual(
			len(frappe.get_all("Event Ticket Type", filters={"event": event_name, "title": "Skipped"})), 0
		)
		self.assertEqual(len(frappe.get_all("Ticket Add-on", filters={"event": event_name})), 0)
		self.assertEqual(len(frappe.get_all("Buzz Custom Field", filters={"event": event_name})), 0)

	def test_create_from_template_sets_default_title_and_date(self):
		"""Test that event gets a default title and today's date"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Defaults Template",
				"category": "Test Category",
				"host": "Test Host",
			}
		)
		template.insert()

		options = {"category": 1, "host": 1}
		event_name = create_from_template(template.name, frappe.as_json(options))
		event = frappe.get_doc("Buzz Event", event_name)

		self.assertIn("Defaults Template", event.title)
		self.assertEqual(str(event.start_date), frappe.utils.today())

	def test_create_from_template_copies_sponsorship_settings(self):
		"""Test that sponsorship settings are copied"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Sponsor Template",
				"category": "Test Category",
				"host": "Test Host",
				"auto_send_pitch_deck": 1,
				"sponsor_deck_reply_to": "test@example.com",
				"sponsor_deck_cc": "cc@example.com",
			}
		)
		template.insert()

		options = {
			"category": 1,
			"host": 1,
			"auto_send_pitch_deck": 1,
			"sponsor_deck_reply_to": 1,
			"sponsor_deck_cc": 1,
		}

		event_name = create_from_template(template.name, frappe.as_json(options))
		event = frappe.get_doc("Buzz Event", event_name)

		self.assertEqual(event.auto_send_pitch_deck, 1)
		self.assertEqual(event.sponsor_deck_reply_to, "test@example.com")
		self.assertEqual(event.sponsor_deck_cc, "cc@example.com")

	# ==================== Save as Template Tests ====================

	def test_save_event_as_template_all_options(self):
		"""Test saving an event as template with all field options"""
		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Full Save Event",
				"category": "Test Category",
				"host": "Test Host",
				"start_date": frappe.utils.today(),
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"about": "Full event description",
				"apply_tax": 1,
				"tax_label": "GST",
				"tax_percentage": 18,
			}
		)
		event.insert()

		# Create linked docs
		frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": event.name,
				"title": "Gold",
				"price": 5000,
				"currency": "INR",
				"is_published": 1,
			}
		).insert()

		frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": event.name,
				"title": "Parking",
				"price": 200,
				"currency": "INR",
				"enabled": 1,
			}
		).insert()

		frappe.get_doc(
			{
				"doctype": "Buzz Custom Field",
				"event": event.name,
				"label": "Designation",
				"fieldname": "designation",
				"fieldtype": "Data",
				"applied_to": "Booking",
				"enabled": 1,
			}
		).insert()

		options = {
			"category": 1,
			"host": 1,
			"medium": 1,
			"about": 1,
			"apply_tax": 1,
			"tax_label": 1,
			"tax_percentage": 1,
			"ticket_types": 1,
			"add_ons": 1,
			"custom_fields": 1,
		}

		template_name = create_template_from_event(
			str(event.name), "Full Save Template", frappe.as_json(options)
		)
		template = frappe.get_doc("Event Template", template_name)

		self.assertEqual(template.category, "Test Category")
		self.assertEqual(template.host, "Test Host")
		self.assertEqual(template.medium, "Online")
		self.assertEqual(template.about, "Full event description")
		self.assertEqual(template.apply_tax, 1)
		self.assertEqual(template.tax_percentage, 18)

		# Check linked docs (ticket types include default "Normal" created on event insert)
		gold_tickets = [t for t in template.template_ticket_types if t.title == "Gold"]
		self.assertEqual(len(gold_tickets), 1)
		self.assertEqual(gold_tickets[0].price, 5000)

		self.assertEqual(len(template.template_add_ons), 1)
		self.assertEqual(template.template_add_ons[0].title, "Parking")

		self.assertEqual(len(template.template_custom_fields), 1)
		self.assertEqual(template.template_custom_fields[0].label, "Designation")

	def test_save_event_as_template_partial(self):
		"""Test saving event as template with partial options"""
		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Partial Save Event",
				"category": "Test Category",
				"host": "Test Host",
				"start_date": frappe.utils.today(),
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"medium": "In Person",
				"about": "Included",
				"apply_tax": 1,
				"tax_percentage": 18,
			}
		)
		event.insert()

		options = {"category": 1, "about": 1, "medium": 0, "apply_tax": 0}

		template_name = create_template_from_event(
			str(event.name), "Partial Save Template", frappe.as_json(options)
		)
		template = frappe.get_doc("Event Template", template_name)

		self.assertEqual(template.category, "Test Category")
		self.assertEqual(template.about, "Included")
		self.assertFalse(template.host)
		self.assertFalse(template.apply_tax)

	# ==================== Round Trip Test ====================

	def test_round_trip_preserves_data(self):
		"""Test Event -> Template -> Event preserves all data"""
		original = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Round Trip Event",
				"category": "Test Category",
				"host": "Test Host",
				"start_date": frappe.utils.today(),
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"about": "Round trip description",
				"apply_tax": 1,
				"tax_label": "Service Tax",
				"tax_percentage": 12,
			}
		)
		original.insert()

		frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": original.name,
				"title": "Platinum",
				"price": 10000,
				"currency": "INR",
				"is_published": 1,
				"max_tickets_available": 25,
			}
		).insert()

		# Event -> Template
		all_options = {
			"category": 1,
			"host": 1,
			"medium": 1,
			"about": 1,
			"apply_tax": 1,
			"tax_label": 1,
			"tax_percentage": 1,
			"ticket_types": 1,
		}
		template_name = create_template_from_event(
			str(original.name), "Round Trip Template", frappe.as_json(all_options)
		)

		# Template -> New Event
		new_event_name = create_from_template(template_name, frappe.as_json(all_options))
		new_event = frappe.get_doc("Buzz Event", new_event_name)

		self.assertEqual(new_event.category, original.category)
		self.assertEqual(new_event.host, original.host)
		self.assertEqual(new_event.medium, original.medium)
		self.assertEqual(new_event.about, original.about)
		self.assertEqual(new_event.tax_label, original.tax_label)
		self.assertEqual(new_event.tax_percentage, original.tax_percentage)

		platinum_tickets = frappe.get_all(
			"Event Ticket Type",
			filters={"event": new_event_name, "title": "Platinum"},
			fields=["price", "max_tickets_available"],
		)
		self.assertEqual(len(platinum_tickets), 1)
		self.assertEqual(platinum_tickets[0].price, 10000)
		self.assertEqual(platinum_tickets[0].max_tickets_available, 25)

	# ==================== Permission Tests ====================

	def test_create_from_template_requires_template_read_permission(self):
		"""Test that creating from template requires read permission on Event Template"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Perm Test Template",
				"category": "Test Category",
				"host": "Test Host",
			}
		)
		template.insert()

		# Create a user without Event Template read permission
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.exceptions.ValidationError):
				create_from_template(template.name, frappe.as_json({"category": 1, "host": 1}))
		finally:
			frappe.set_user("Administrator")

	def test_save_as_template_requires_create_permission(self):
		"""Test that saving as template requires create permission on Event Template"""
		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Perm Event",
				"category": "Test Category",
				"host": "Test Host",
				"start_date": frappe.utils.today(),
				"start_time": "09:00:00",
				"end_time": "18:00:00",
			}
		)
		event.insert()

		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.exceptions.ValidationError):
				create_template_from_event(str(event.name), "Perm Template", frappe.as_json({"category": 1}))
		finally:
			frappe.set_user("Administrator")


class TestRegistrationsClosed(FrappeTestCase):
	"""Tests for the are_registrations_closed function with timezone handling."""

	def _make_event(
		self,
		registrations_close_at=None,
		time_zone=None,
		start_date="2026-06-01",
		start_time="09:00:00",
		end_date="2026-06-01",
		end_time="18:00:00",
	):
		"""Create a minimal event _dict for testing (no DB insert needed).

		Defaults start/end to a fixed date far from any fake "now" used in the
		explicit-close_at tests, so the event-end fallback never accidentally
		kicks in for those.
		"""
		return frappe._dict(
			registrations_close_at=registrations_close_at,
			time_zone=time_zone,
			start_date=start_date,
			start_time=start_time,
			end_date=end_date,
			end_time=end_time,
		)

	def test_no_close_at_and_event_in_future_returns_false(self):
		"""When registrations_close_at is not set and the event hasn't ended, registrations are open."""
		fake_now = datetime(2026, 6, 15, 10, 0, 0)
		event = self._make_event(
			time_zone="UTC",
			start_date="2026-06-20",
			start_time="09:00:00",
			end_date="2026-06-20",
			end_time="18:00:00",
		)
		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_now):
			self.assertFalse(are_registrations_closed(event))

	def test_no_close_at_falls_back_to_event_end(self):
		"""When registrations_close_at is not set, registrations close once the event itself has ended (issue #91)."""
		fake_now = datetime(2026, 6, 15, 20, 0, 0)
		event = self._make_event(
			time_zone="UTC",
			start_date="2026-06-15",
			start_time="09:00:00",
			end_date="2026-06-15",
			end_time="18:00:00",  # event ended 2 hours before fake_now
		)
		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_now):
			self.assertTrue(are_registrations_closed(event))

	def test_close_at_takes_priority_over_event_end(self):
		"""An explicit registrations_close_at overrides the event-end fallback, even when it's later than the event end."""
		fake_now = datetime(2026, 6, 15, 19, 0, 0)  # after event end (18:00), before close_at (20:00)
		event = self._make_event(
			registrations_close_at="2026-06-15 20:00:00",
			time_zone="UTC",
			start_date="2026-06-15",
			start_time="09:00:00",
			end_date="2026-06-15",
			end_time="18:00:00",
		)
		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_now):
			self.assertFalse(are_registrations_closed(event))

	def test_future_close_at_returns_false(self):
		"""When close_at is in the future, registrations are open."""
		fake_now = datetime(2026, 6, 15, 10, 0, 0)
		event = self._make_event(
			registrations_close_at="2026-06-15 12:00:00",  # 2 hours after fake_now
			time_zone="UTC",
		)
		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_now):
			self.assertFalse(are_registrations_closed(event))

	def test_past_close_at_returns_true(self):
		"""When close_at is in the past, registrations are closed."""
		fake_now = datetime(2026, 6, 15, 14, 0, 0)
		event = self._make_event(
			registrations_close_at="2026-06-15 12:00:00",  # 2 hours before fake_now
			time_zone="UTC",
		)
		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_now):
			self.assertTrue(are_registrations_closed(event))

	def test_timezone_ahead_of_utc_closes_earlier(self):
		"""An event in Asia/Kolkata (UTC+5:30) should close before the same wall-clock time in UTC.

		If it's 14:00 UTC, that's 19:30 IST.
		A close_at of 18:00 (naive, in event tz) is already past in IST but not in UTC.
		"""
		# Simulate 19:30 IST (= 14:00 UTC)
		fake_ist_now = datetime(2026, 6, 15, 19, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))

		event = self._make_event(
			registrations_close_at="2026-06-15 18:00:00",  # 18:00 in event tz (IST)
			time_zone="Asia/Kolkata",
		)

		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_ist_now):
			# 19:30 IST > 18:00 IST → closed
			self.assertTrue(are_registrations_closed(event))

	def test_timezone_behind_utc_stays_open_longer(self):
		"""An event in US/Pacific (UTC-7) should stay open longer than the same wall-clock in UTC.

		If it's 23:00 UTC on June 15, that's 16:00 PDT on June 15.
		A close_at of 18:00 (naive, in event tz) is still in the future in PDT.
		"""
		# Simulate 16:00 PDT (= 23:00 UTC)
		fake_pdt_now = datetime(2026, 6, 15, 16, 0, 0, tzinfo=timezone(timedelta(hours=-7)))

		event = self._make_event(
			registrations_close_at="2026-06-15 18:00:00",  # 18:00 in event tz (PDT)
			time_zone="US/Pacific",
		)

		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_pdt_now):
			# 16:00 PDT < 18:00 PDT → still open
			self.assertFalse(are_registrations_closed(event))

	def test_same_close_time_different_timezones(self):
		"""Same UTC instant, same close_at string — different result depending on event timezone.

		At 2026-06-15 17:30 UTC:
		  - Asia/Kolkata: 23:00 IST → 23:00 > 18:00 → closed
		  - US/Pacific:   10:30 PDT → 10:30 < 18:00 → open
		"""
		close_at = "2026-06-15 18:00:00"

		event_ist = self._make_event(registrations_close_at=close_at, time_zone="Asia/Kolkata")
		event_pdt = self._make_event(registrations_close_at=close_at, time_zone="US/Pacific")

		# 17:30 UTC = 23:00 IST
		fake_ist_now = datetime(2026, 6, 15, 23, 0, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_ist_now):
			self.assertTrue(are_registrations_closed(event_ist))

		# 17:30 UTC = 10:30 PDT
		fake_pdt_now = datetime(2026, 6, 15, 10, 30, 0, tzinfo=timezone(timedelta(hours=-7)))
		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_pdt_now):
			self.assertFalse(are_registrations_closed(event_pdt))

	def test_falls_back_to_system_timezone_when_event_tz_not_set(self):
		"""When event has no time_zone, system timezone is used."""
		fake_now = datetime(2026, 6, 15, 14, 0, 0)
		event = self._make_event(
			registrations_close_at="2026-06-15 13:00:00",  # 1 hour before fake_now
			time_zone=None,
		)
		with patch("buzz.api.get_datetime_in_timezone", return_value=fake_now):
			self.assertTrue(are_registrations_closed(event))

	def test_closing_moment_is_same_absolute_instant_for_viewers_anywhere(self):
		"""are_registrations_closed never looks at the viewer's timezone, only the event's -
		so a person checking from London and a person checking from Mumbai at the exact same
		real-world moment always get the same open/closed answer.

		Worked example: event in Asia/Kolkata (IST, UTC+5:30) closes at 16:30 IST.
		London in June is on BST (UTC+1:00). Offset difference: 4:30.
		So the closing instant is simultaneously:
		  2026-06-15 11:00:00 UTC
		  2026-06-15 12:00:00 BST  (noon in London)
		  2026-06-15 16:30:00 IST  (4:30 PM in India - the configured close time)
		`get_datetime_in_timezone` (mocked here, as elsewhere in this class) always returns
		"now" already converted into the *event's* timezone - so regardless of where the
		actual request came from, this test only needs to supply the IST-side value that
		corresponds to that one shared real-world instant.
		"""
		event = self._make_event(registrations_close_at="2026-06-15 16:30:00", time_zone="Asia/Kolkata")

		# Exactly at the closing instant (11:00 UTC / noon BST / 16:30 IST) -> comparison is
		# strictly-greater-than, so registrations are still open at the exact boundary.
		at_close = datetime(2026, 6, 15, 16, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
		with patch("buzz.api.get_datetime_in_timezone", return_value=at_close):
			self.assertFalse(are_registrations_closed(event))

		# One minute before that shared instant (10:59 UTC / 11:59 BST / 16:29 IST) -> still open.
		before_close = datetime(2026, 6, 15, 16, 29, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
		with patch("buzz.api.get_datetime_in_timezone", return_value=before_close):
			self.assertFalse(are_registrations_closed(event))

		# One minute after (11:01 UTC / 12:01 BST / 16:31 IST) -> closed.
		after_close = datetime(2026, 6, 15, 16, 31, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
		with patch("buzz.api.get_datetime_in_timezone", return_value=after_close):
			self.assertTrue(are_registrations_closed(event))

	def test_event_end_fallback_is_also_timezone_consistent(self):
		"""Same India/London worked example as above, but for the no-explicit-cutoff fallback
		path: the event's own end_date/end_time (16:30 IST) is what closes registrations.
		"""
		event = self._make_event(
			time_zone="Asia/Kolkata",
			start_date="2026-06-15",
			start_time="09:00:00",
			end_date="2026-06-15",
			end_time="16:30:00",
		)

		# 16:29 IST (11:59 BST / noon-minus-1 in London) -> event still ongoing, open.
		before_end = datetime(2026, 6, 15, 16, 29, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
		with patch("buzz.api.get_datetime_in_timezone", return_value=before_end):
			self.assertFalse(are_registrations_closed(event))

		# 16:31 IST (12:01 BST, just past noon in London) -> event over, closed.
		after_end = datetime(2026, 6, 15, 16, 31, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
		with patch("buzz.api.get_datetime_in_timezone", return_value=after_end):
			self.assertTrue(are_registrations_closed(event))
