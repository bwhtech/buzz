from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.events import convert_to_zoom_meeting
from buzz.api.events.exceptions import CannotManageEvent, EventEnded
from buzz.api.events.test_events import create_event
from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.test_permissions import add_member
from buzz.utils import is_app_installed


def book_meeting(event: BuzzEvent):
	"""The real booking calls Zoom on insert, so the row goes straight to the table."""
	meeting = frappe.get_doc({"doctype": "Zoom Meeting", "name": "ZOOM-TEST", "title": event.title})
	meeting.db_insert()
	event.db_set("zoom_meeting", meeting.name)


class TestConvertToZoomMeeting(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.owner = create_user("zoom-owner@example.com", "Owner")
		cls.viewer = create_user("zoom-viewer@example.com", "Viewer")
		cls.team = create_owned_team("Zoom Team", cls.owner)
		add_member(cls.team, cls.viewer, "Viewer")

	def setUp(self):
		if not is_app_installed("zoom_integration"):
			self.skipTest("zoom_integration is not installed on this site")
		frappe.set_user("Administrator")
		venue = frappe.get_doc(
			{
				"doctype": "Event Venue",
				"venue_name": "Zoom Hall",
				"address": "1 Zoom Street",
				"team": self.team,
			}
		).insert(ignore_permissions=True)
		self.event = create_event("Zoom Event", self.team, medium="In Person", venue=venue.name)
		frappe.set_user(self.owner)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_converts_and_reuses_the_linked_meeting(self):
		with patch.object(
			BuzzEvent, "create_meeting_on_zoom", autospec=True, side_effect=book_meeting
		) as book:
			convert_to_zoom_meeting(self.event)
			frappe.db.set_value("Buzz Event", self.event, "medium", "In Person")
			convert_to_zoom_meeting(self.event)

		event = frappe.get_doc("Buzz Event", self.event)
		self.assertEqual(event.medium, "Online")
		self.assertFalse(event.venue)
		self.assertEqual(event.zoom_meeting, "ZOOM-TEST")
		book.assert_called_once()

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
			patch.object(BuzzEvent, "create_meeting_on_zoom") as book,
		):
			with self.assertRaises(frappe.ValidationError):
				convert_to_zoom_meeting(self.event)

		book.assert_not_called()

	def test_a_viewer_cannot_convert(self):
		frappe.set_user(self.viewer)

		with self.assertRaises(CannotManageEvent):
			convert_to_zoom_meeting(self.event)

	def test_an_ended_event_cannot_be_converted(self):
		yesterday = add_days(today(), -1)
		frappe.db.set_value("Buzz Event", self.event, {"start_date": yesterday, "end_date": None})

		with patch.object(BuzzEvent, "create_meeting_on_zoom") as book:
			with self.assertRaises(EventEnded):
				convert_to_zoom_meeting(self.event)

		book.assert_not_called()
		self.assertEqual(frappe.db.get_value("Buzz Event", self.event, "medium"), "In Person")
