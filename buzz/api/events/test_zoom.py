from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.events import convert_to_zoom_meeting
from buzz.api.events.exceptions import CannotManageEvent, EventEnded
from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory
from buzz.utils import is_app_installed

MEETING_CONTROLLER = "zoom_integration.zoom_integration.doctype.zoom_meeting.zoom_meeting"
CREATE_MEETING_ON_ZOOM = BuzzEvent.create_meeting_on_zoom


class TestConvertToZoomMeeting(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("zoom-owner@example.com").name
		cls.viewer = UserFactory.create_once("zoom-viewer@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")

	def setUp(self):
		if not is_app_installed("zoom_integration"):
			self.skipTest("zoom_integration is not installed on this site")
		self.event = str(BuzzEventFactory.create("in_person", team=self.team).name)
		self.enterContext(self.set_user(self.owner))

	def test_converts_and_reuses_the_linked_meeting(self):
		from zoom_integration.tests.zoom_fixtures import create_meeting_response

		response = create_meeting_response()
		with (
			patch(f"{MEETING_CONTROLLER}.create_zoom_session", return_value=response) as create_zoom_session,
			patch.object(
				BuzzEvent,
				"create_meeting_on_zoom",
				autospec=True,
				side_effect=self.create_meeting_as_administrator,
			),
		):
			convert_to_zoom_meeting(self.event)
			frappe.db.set_value("Buzz Event", self.event, "medium", "In Person")
			convert_to_zoom_meeting(self.event)

		event = frappe.get_doc("Buzz Event", self.event)
		self.assertEqual(event.medium, "Online")
		self.assertFalse(event.venue)
		self.assertEqual(event.zoom_meeting, str(response["id"]))
		create_zoom_session.assert_called_once()

	def test_a_zoom_failure_changes_nothing(self):
		# The request rolls back on the error; the savepoint stands in for it.
		frappe.db.savepoint("zoom_conversion")
		with patch.object(BuzzEvent, "create_meeting_on_zoom", side_effect=Exception("Zoom is down")):
			with self.assertRaises(Exception):
				convert_to_zoom_meeting(self.event)
		frappe.db.rollback(save_point="zoom_conversion")

		event = frappe.get_doc("Buzz Event", self.event)
		self.assertEqual(event.medium, "In Person")
		self.assertTrue(event.venue)

	def test_a_failed_save_books_no_meeting(self):
		with (
			patch.object(BuzzEvent, "validate", side_effect=frappe.ValidationError),
			patch.object(BuzzEvent, "create_meeting_on_zoom") as create_meeting,
		):
			with self.assertRaises(frappe.ValidationError):
				convert_to_zoom_meeting(self.event)

		create_meeting.assert_not_called()

	def test_a_viewer_cannot_convert(self):
		with self.set_user(self.viewer), self.assertRaises(CannotManageEvent):
			convert_to_zoom_meeting(self.event)

	def test_an_ended_event_cannot_be_converted(self):
		yesterday = add_days(today(), -1)
		frappe.db.set_value("Buzz Event", self.event, {"start_date": yesterday, "end_date": None})

		with patch.object(BuzzEvent, "create_meeting_on_zoom") as create_meeting:
			with self.assertRaises(EventEnded):
				convert_to_zoom_meeting(self.event)

		create_meeting.assert_not_called()
		self.assertEqual(frappe.db.get_value("Buzz Event", self.event, "medium"), "In Person")

	def create_meeting_as_administrator(self, event: BuzzEvent):
		"""The real booking, as Administrator: an organiser holds no Zoom Meeting permission."""
		with self.set_user("Administrator"):
			return CREATE_MEETING_ON_ZOOM(event)
