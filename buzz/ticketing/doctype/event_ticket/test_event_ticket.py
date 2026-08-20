# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.utils import generate_qr_code_file, make_qr_image, render_email_template

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Bulk Ticket Coupon"]


class TestEventTicketEmail(IntegrationTestCase):
	"""Tests for Event Ticket email sending with template fallback logic."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		cls.test_event.ticket_email_template = None
		cls.test_event.save()

		# Clear global settings
		settings = frappe.get_doc("Buzz Settings")
		settings.default_ticket_email_template = None
		settings.save()

	def setUp(self):
		self.test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.test_event.name,
				"title": "Email Test Ticket",
				"price": 100,
			}
		).insert()

		self.test_ticket = frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"event": self.test_event.name,
				"ticket_type": self.test_ticket_type.name,
				"attendee_name": "Test Attendee",
				"attendee_email": "test@example.com",
			}
		).insert()

	def tearDown(self):
		frappe.delete_doc("Event Ticket", self.test_ticket.name, force=True)
		frappe.delete_doc("Event Ticket Type", self.test_ticket_type.name, force=True)

	def _create_template(self, name, subject_prefix):
		if frappe.db.exists("Email Template", name):
			frappe.delete_doc("Email Template", name, force=True)
		return frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": name,
				"subject": f"{subject_prefix} - {{{{ event_title }}}}",
				"response": f"<p>{subject_prefix} content</p>",
			}
		).insert()

	@patch("frappe.sendmail")
	def test_uses_event_template_when_set(self, mock_sendmail):
		template = self._create_template("Event Ticket Template", "EVENT")
		try:
			self.test_event.ticket_email_template = template.name
			self.test_event.save()

			self.test_ticket.send_ticket_email(now=True)

			mock_sendmail.assert_called_once()
			self.assertIn("EVENT", mock_sendmail.call_args[1]["subject"])
		finally:
			self.test_event.ticket_email_template = None
			self.test_event.save()
			frappe.delete_doc("Email Template", template.name, force=True)

	@patch("frappe.sendmail")
	def test_falls_back_to_global_template(self, mock_sendmail):
		template = self._create_template("Global Ticket Template", "GLOBAL")
		try:
			self.test_event.ticket_email_template = None
			self.test_event.save()

			settings = frappe.get_doc("Buzz Settings")
			settings.default_ticket_email_template = template.name
			settings.save()

			self.test_ticket.send_ticket_email(now=True)

			mock_sendmail.assert_called_once()
			self.assertIn("GLOBAL", mock_sendmail.call_args[1]["subject"])
		finally:
			settings.default_ticket_email_template = None
			settings.save()
			frappe.delete_doc("Email Template", template.name, force=True)

	@patch("frappe.sendmail")
	def test_event_template_takes_precedence(self, mock_sendmail):
		event_template = self._create_template("Event Template", "EVENT")
		global_template = self._create_template("Global Template", "GLOBAL")
		try:
			self.test_event.ticket_email_template = event_template.name
			self.test_event.save()

			settings = frappe.get_doc("Buzz Settings")
			settings.default_ticket_email_template = global_template.name
			settings.save()

			self.test_ticket.send_ticket_email(now=True)

			mock_sendmail.assert_called_once()
			self.assertIn("EVENT", mock_sendmail.call_args[1]["subject"])
			self.assertNotIn("GLOBAL", mock_sendmail.call_args[1]["subject"])
		finally:
			self.test_event.ticket_email_template = None
			self.test_event.save()
			settings.default_ticket_email_template = None
			settings.save()
			frappe.delete_doc("Email Template", event_template.name, force=True)
			frappe.delete_doc("Email Template", global_template.name, force=True)

	@patch("frappe.sendmail")
	def test_uses_inline_template_when_none_configured(self, mock_sendmail):
		self.test_event.ticket_email_template = None
		self.test_event.save()

		settings = frappe.get_doc("Buzz Settings")
		settings.default_ticket_email_template = None
		settings.save()

		self.test_ticket.send_ticket_email(now=True)

		mock_sendmail.assert_called_once()
		self.assertEqual(mock_sendmail.call_args[1]["template"], "ticket")


class TestQRCodeGeneration(IntegrationTestCase):
	"""Tests for QR code generation utility."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

	def test_make_qr_image_returns_png_bytes(self):
		"""QR image generation should return valid PNG bytes."""
		result = make_qr_image("test-data-123")

		self.assertIsInstance(result, bytes)
		# PNG magic bytes
		self.assertTrue(result.startswith(b"\x89PNG"))

	def test_generate_qr_code_file_creates_attachment(self):
		"""QR code file should be created and attached to document."""
		file_url = generate_qr_code_file(
			doc=self.test_event,
			data="test-qr-data",
			field_name="qr_code",
			file_prefix="test-qr",
		)

		self.assertIsNotNone(file_url)
		self.assertTrue(file_url.endswith(".png"))

		# Verify file exists in File doctype
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		self.assertEqual(file_doc.attached_to_doctype, "Buzz Event")
		self.assertEqual(str(file_doc.attached_to_name), str(self.test_event.name))

		# Cleanup
		file_doc.delete()


class TestEventTicketZoomMeeting(IntegrationTestCase):
	def setUp(self):
		# tearDown rolls back, so the fixtures are rebuilt per test rather than per class.
		super().setUp()
		self.event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self.ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"title": "Meeting TT",
				"event": self.event.name,
				"currency": "USD",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

	def tearDown(self):
		frappe.db.rollback()

	def _submit_ticket(self, email="alice@example.com"):
		ticket = frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"event": self.event.name,
				"ticket_type": self.ticket_type.name,
				"first_name": "Alice",
				"last_name": "Smith",
				"attendee_email": email,
			}
		).insert(ignore_permissions=True)
		ticket.submit()
		return ticket

	def test_ticket_registration_points_at_the_events_zoom_meeting(self):
		from zoom_integration.tests.zoom_fixtures import (
			add_meeting_registrant_response,
			create_meeting_response,
		)

		meeting_controller = "zoom_integration.zoom_integration.doctype.zoom_meeting.zoom_meeting"

		with patch(f"{meeting_controller}.create_zoom_session", return_value=create_meeting_response()):
			meeting = frappe.get_doc(
				{
					"doctype": "Zoom Meeting",
					"title": "Ticket Meeting",
					"date": "2026-08-01",
					"start_time": "10:00:00",
					"duration": 3600,
					"timezone": "Asia/Calcutta",
				}
			).insert(ignore_permissions=True)

		self.event.db_set("zoom_meeting", meeting.name)
		registrant = add_meeting_registrant_response()

		with patch(f"{meeting_controller}.add_zoom_registrant", return_value=registrant):
			ticket = self._submit_ticket()

		self.assertTrue(ticket.zoom_session_registration)
		registration = frappe.get_doc("Zoom Session Registration", ticket.zoom_session_registration)
		self.assertEqual(registration.reference_doctype, "Zoom Meeting")
		self.assertEqual(registration.reference_name, meeting.name)
		self.assertEqual(registration.registrant_id, registrant["registrant_id"])

	def test_ticket_registration_points_at_the_events_zoom_webinar(self):
		from zoom_integration.tests.zoom_fixtures import (
			add_webinar_registrant_response,
			create_webinar_response,
			mock_zoom_post,
		)

		webinar_controller = "zoom_integration.zoom_integration.doctype.zoom_webinar.zoom_webinar"

		with mock_zoom_post(webinar_controller, 201, create_webinar_response()):
			webinar = frappe.get_doc(
				{
					"doctype": "Zoom Webinar",
					"title": "Ticket Webinar",
					"date": "2026-08-01",
					"start_time": "10:00:00",
					"duration": 3600,
					"timezone": "Asia/Calcutta",
				}
			).insert(ignore_permissions=True)

		self.event.db_set("zoom_webinar", webinar.name)
		registrant = add_webinar_registrant_response()

		with mock_zoom_post(webinar_controller, 200, registrant):
			ticket = self._submit_ticket("carol@example.com")

		registration = frappe.get_doc("Zoom Session Registration", ticket.zoom_session_registration)
		self.assertEqual(registration.reference_doctype, "Zoom Webinar")
		self.assertEqual(registration.reference_name, webinar.name)
		self.assertEqual(registration.registrant_id, registrant["registrant_id"])

	def test_ticket_details_expose_the_zoom_session_reference(self):
		from zoom_integration.tests.zoom_fixtures import (
			add_meeting_registrant_response,
			create_meeting_response,
		)

		from buzz.api.tickets import get_ticket_details

		meeting_controller = "zoom_integration.zoom_integration.doctype.zoom_meeting.zoom_meeting"

		with patch(f"{meeting_controller}.create_zoom_session", return_value=create_meeting_response()):
			meeting = frappe.get_doc(
				{
					"doctype": "Zoom Meeting",
					"title": "Details Meeting",
					"date": "2026-08-01",
					"start_time": "10:00:00",
					"duration": 3600,
					"timezone": "Asia/Calcutta",
				}
			).insert(ignore_permissions=True)

		self.event.db_set("zoom_meeting", meeting.name)
		registrant = add_meeting_registrant_response()

		with patch(f"{meeting_controller}.add_zoom_registrant", return_value=registrant):
			ticket = self._submit_ticket("dana@example.com")

		details = get_ticket_details(ticket.name)

		self.assertEqual(details.zoom_join_url, registrant["join_url"])
		self.assertEqual(details.zoom_reference_doctype, "Zoom Meeting")
		self.assertEqual(details.zoom_reference_name, meeting.name)


class TestRenderEmailTemplate(IntegrationTestCase):
	"""Attendees and sponsors are Website Users; only Desk Users can read an Email Template."""

	def tearDown(self):
		frappe.db.rollback()

	def test_renders_for_a_user_without_email_template_permission(self):
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": "Unprivileged Render Template",
				"subject": "NOPERM - {{ event_title }}",
				"response": "<p>NOPERM content</p>",
			}
		).insert(ignore_permissions=True)

		attendee = "attendee-render@example.com"
		if not frappe.db.exists("User", attendee):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": attendee,
					"first_name": "Attendee",
					"user_type": "Website User",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		self.addCleanup(frappe.set_user, frappe.session.user)
		frappe.set_user(attendee)
		self.assertFalse(frappe.has_permission("Email Template", "read"))

		rendered = render_email_template(template.name, {"event_title": "Buzz Conf"})

		self.assertEqual(rendered["subject"], "NOPERM - Buzz Conf")
		self.assertIn("NOPERM content", rendered["message"])


class TestGuestTicketEmail(IntegrationTestCase):
	"""Public bookings submit their tickets as Guest."""

	def setUp(self):
		self.event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self.ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event.name,
				"title": "Guest Email Ticket",
				"price": 0,
			}
		).insert(ignore_permissions=True)
		self.template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": "Guest Ticket Template",
				"subject": "GUEST - {{ event_title }}",
				"response": "<p>Guest content</p>",
			}
		).insert(ignore_permissions=True)
		self.event.db_set("ticket_email_template", self.template.name)
		self.addCleanup(frappe.set_user, frappe.session.user)

	def tearDown(self):
		frappe.db.rollback()

	@patch("frappe.sendmail")
	def test_guest_can_render_the_ticket_email_template(self, mock_sendmail):
		ticket = frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"event": self.event.name,
				"ticket_type": self.ticket_type.name,
				"first_name": "Guest",
				"attendee_email": "guest-booking@example.com",
			}
		).insert(ignore_permissions=True)

		frappe.set_user("Guest")

		ticket.send_ticket_email(now=True)

		mock_sendmail.assert_called_once()
		self.assertIn("GUEST", mock_sendmail.call_args[1]["subject"])
