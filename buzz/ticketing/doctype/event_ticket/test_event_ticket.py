# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	EmailTemplateFactory,
	EventTicketFactory,
	UserFactory,
)
from buzz.utils import generate_qr_code_file, render_email_template

MEETING_CONTROLLER = "zoom_integration.zoom_integration.doctype.zoom_meeting.zoom_meeting"
WEBINAR_CONTROLLER = "zoom_integration.zoom_integration.doctype.zoom_webinar.zoom_webinar"


class TestEventTicketEmail(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()
		cls.event_template = EmailTemplateFactory.create(subject="Event ticket template").name
		cls.team_template = EmailTemplateFactory.create(subject="Team ticket template").name

	def setUp(self):
		self.set_templates(event_template=None, team_template=None)
		self.ticket = EventTicketFactory.create(event=self.event.name)

	@patch("frappe.sendmail")
	def test_uses_event_template_when_set(self, mock_sendmail):
		self.set_templates(event_template=self.event_template, team_template=None)

		self.ticket.send_ticket_email(now=True)

		mock_sendmail.assert_called_once()
		self.assertEqual(mock_sendmail.call_args[1]["subject"], "Event ticket template")

	@patch("frappe.sendmail")
	def test_falls_back_to_the_teams_default_template(self, mock_sendmail):
		self.set_templates(event_template=None, team_template=self.team_template)

		self.ticket.send_ticket_email(now=True)

		mock_sendmail.assert_called_once()
		self.assertEqual(mock_sendmail.call_args[1]["subject"], "Team ticket template")

	@patch("frappe.sendmail")
	def test_event_template_takes_precedence(self, mock_sendmail):
		self.set_templates(event_template=self.event_template, team_template=self.team_template)

		self.ticket.send_ticket_email(now=True)

		mock_sendmail.assert_called_once()
		self.assertEqual(mock_sendmail.call_args[1]["subject"], "Event ticket template")

	@patch("frappe.sendmail")
	def test_uses_inline_template_when_none_configured(self, mock_sendmail):
		self.ticket.send_ticket_email(now=True)

		mock_sendmail.assert_called_once()
		self.assertEqual(mock_sendmail.call_args[1]["template"], "ticket")

	@patch("frappe.sendmail")
	def test_support_email_reaches_the_template_from_the_team(self, mock_sendmail):
		BuzzTeamFactory.set_settings(self.event.team, {"support_email": "team-support@example.com"})
		self.addCleanup(BuzzTeamFactory.set_settings, self.event.team, {"support_email": None})

		self.ticket.send_ticket_email(now=True)

		self.assertEqual(mock_sendmail.call_args[1]["args"]["support_email"], "team-support@example.com")

	def set_templates(self, event_template: str | None, team_template: str | None):
		frappe.db.set_value("Buzz Event", self.event.name, "ticket_email_template", event_template)
		frappe.clear_document_cache("Buzz Event", self.event.name)
		BuzzTeamFactory.set_settings(self.event.team, {"default_ticket_email_template": team_template})


class TestQRCodeGeneration(IntegrationTestCase):
	def test_generate_qr_code_file_creates_attachment(self):
		event = BuzzEventFactory.create()

		file_url = generate_qr_code_file(doc=event, data="test-qr-data", file_prefix="test-qr")

		self.assertTrue(file_url.endswith(".png"))
		qr_file = frappe.get_doc("File", {"file_url": file_url})
		self.addCleanup(qr_file.delete)
		self.assertEqual(qr_file.attached_to_doctype, "Buzz Event")
		self.assertEqual(qr_file.attached_to_name, str(event.name))


class TestEventTicketZoomMeeting(IntegrationTestCase):
	def setUp(self):
		# Each test links its own Zoom session, so each needs its own event.
		self.event = BuzzEventFactory.create()

	def test_ticket_registration_points_at_the_events_zoom_meeting(self):
		from zoom_integration.tests.zoom_fixtures import add_meeting_registrant_response

		meeting = self.create_zoom_meeting()
		registrant = add_meeting_registrant_response()

		with patch(f"{MEETING_CONTROLLER}.add_zoom_registrant", return_value=registrant):
			ticket = self.submit_ticket()

		self.assertTrue(ticket.zoom_session_registration)
		self.assert_registration(ticket, "Zoom Meeting", meeting, registrant)

	def test_ticket_registration_points_at_the_events_zoom_webinar(self):
		from zoom_integration.tests.zoom_fixtures import (
			add_webinar_registrant_response,
			create_webinar_response,
			mock_zoom_post,
		)

		with mock_zoom_post(WEBINAR_CONTROLLER, 201, create_webinar_response()):
			webinar = self.event.create_webinar_on_zoom().name
		registrant = add_webinar_registrant_response()

		with mock_zoom_post(WEBINAR_CONTROLLER, 200, registrant):
			ticket = self.submit_ticket()

		self.assert_registration(ticket, "Zoom Webinar", webinar, registrant)

	def test_ticket_details_expose_the_zoom_session_reference(self):
		from zoom_integration.tests.zoom_fixtures import add_meeting_registrant_response

		from buzz.api.tickets import get_ticket_details

		meeting = self.create_zoom_meeting()
		registrant = add_meeting_registrant_response()

		with patch(f"{MEETING_CONTROLLER}.add_zoom_registrant", return_value=registrant):
			ticket = self.submit_ticket()

		details = get_ticket_details(ticket.name)
		self.assertEqual(details.zoom_join_url, registrant["join_url"])
		self.assertEqual(
			(details.zoom_reference_doctype, details.zoom_reference_name), ("Zoom Meeting", meeting)
		)

	def create_zoom_meeting(self) -> str:
		from zoom_integration.tests.zoom_fixtures import create_meeting_response

		with patch(f"{MEETING_CONTROLLER}.create_zoom_session", return_value=create_meeting_response()):
			return self.event.create_meeting_on_zoom().name

	def submit_ticket(self):
		# The ticket reads the linked session from the cached event.
		frappe.clear_document_cache("Buzz Event", self.event.name)
		return EventTicketFactory.create("submitted", event=self.event.name)

	def assert_registration(self, ticket, reference_doctype: str, reference_name: str, registrant: dict):
		registration = frappe.get_doc("Zoom Session Registration", ticket.zoom_session_registration)
		self.assertEqual(registration.reference_doctype, reference_doctype)
		self.assertEqual(registration.reference_name, reference_name)
		self.assertEqual(registration.registrant_id, registrant["registrant_id"])


class TestRenderEmailTemplate(IntegrationTestCase):
	"""Attendees and sponsors are Website Users; only Desk Users can read an Email Template."""

	def test_renders_for_a_user_without_email_template_permission(self):
		template = EmailTemplateFactory.create(
			subject="NOPERM - {{ event_title }}", response="<p>NOPERM content</p>"
		).name
		attendee = UserFactory.create_once("ticket-render-attendee@example.com").name

		with self.set_user(attendee):
			self.assertFalse(frappe.has_permission("Email Template", "read"))
			rendered = render_email_template(template, {"event_title": "Buzz Conf"})

		self.assertEqual(rendered["subject"], "NOPERM - Buzz Conf")
		self.assertIn("NOPERM content", rendered["message"])


class TestGuestTicketEmail(IntegrationTestCase):
	"""Public bookings submit their tickets as Guest."""

	@patch("frappe.sendmail")
	def test_guest_can_render_the_ticket_email_template(self, mock_sendmail):
		event = BuzzEventFactory.create()
		template = EmailTemplateFactory.create(subject="Guest ticket template").name
		frappe.db.set_value("Buzz Event", event.name, "ticket_email_template", template)
		frappe.clear_document_cache("Buzz Event", event.name)
		ticket = EventTicketFactory.create(event=event.name)

		with self.set_user("Guest"):
			ticket.send_ticket_email(now=True)

		mock_sendmail.assert_called_once()
		self.assertEqual(mock_sendmail.call_args[1]["subject"], "Guest ticket template")
