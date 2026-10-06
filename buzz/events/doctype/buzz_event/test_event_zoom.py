from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory

MEETING_CONTROLLER = "zoom_integration.zoom_integration.doctype.zoom_meeting.zoom_meeting"
WEBINAR_CONTROLLER = "zoom_integration.zoom_integration.doctype.zoom_webinar.zoom_webinar.ZoomWebinar"


class TestBuzzEventZoomMeeting(IntegrationTestCase):
	def setUp(self):
		self.event = BuzzEventFactory.create()

	def test_create_meeting_on_zoom_links_meeting_to_event(self):
		from zoom_integration.tests.zoom_fixtures import create_meeting_response

		response = create_meeting_response()
		with patch(f"{MEETING_CONTROLLER}.create_zoom_session", return_value=response):
			meeting = self.event.create_meeting_on_zoom()

		self.event.reload()
		self.assertEqual(self.event.zoom_meeting, meeting.name)
		self.assertEqual(meeting.zoom_meeting_id, str(response["id"]))

	def test_event_stores_the_zoom_meeting_id_the_desk_link_is_built_from(self):
		from zoom_integration.tests.zoom_fixtures import create_meeting_response

		response = create_meeting_response()
		with patch(f"{MEETING_CONTROLLER}.create_zoom_session", return_value=response):
			self.event.create_meeting_on_zoom()

		self.event.reload()
		self.assertEqual(self.event.zoom_meeting, str(response["id"]))

	def test_update_event_schedule_pushes_to_zoom_meeting(self):
		from zoom_integration.tests.zoom_fixtures import CREATE_MEETING_RESPONSE

		with patch(f"{MEETING_CONTROLLER}.create_zoom_session", return_value=CREATE_MEETING_RESPONSE):
			self.event.create_meeting_on_zoom()

		# No reload(): Time fields come back as timedelta and fail the time check.
		with patch(f"{MEETING_CONTROLLER}.update_zoom_session") as update_zoom_session:
			self.event.end_time = "12:00:00"
			self.event.save()

		update_zoom_session.assert_called_once()
		self.assertEqual(update_zoom_session.call_args.args[0], "meetings")

	def test_webinar_template_comes_from_the_events_team(self):
		template = self.create_webinar_template()
		BuzzTeamFactory.set_settings(self.event.team, {"default_webinar_template": template})
		# Rollback restores the row but not its cached copy.
		self.addCleanup(frappe.clear_document_cache, "Buzz Team Settings", self.event.team)

		with patch(
			f"{WEBINAR_CONTROLLER}.create_webinar_on_zoom",
			autospec=True,
			side_effect=self.set_fake_webinar_id,
		):
			webinar = self.event.create_webinar_on_zoom()

		self.assertEqual(webinar.template, template)

	def create_webinar_template(self) -> str:
		"""Zoom is an optional app, so Buzz owns no factory for its doctypes."""
		name = f"Webinar Template {frappe.generate_hash(length=6)}"
		frappe.get_doc(doctype="Zoom Webinar Template", id=name, title=name, type=1).insert()
		return name

	@staticmethod
	def set_fake_webinar_id(webinar):
		"""Replaces the Zoom API call; validation needs the id."""
		webinar.zoom_webinar_id = "1234567890"
