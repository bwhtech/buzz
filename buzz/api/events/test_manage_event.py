import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.events import create_event, get_event
from buzz.api.events.exceptions import (
	CannotCreateEvents,
	CannotManageEvent,
	EventNotFound,
	ZoomNotAvailable,
)
from buzz.api.events.schemas import NewEvent
from buzz.api.events.services import DEFAULT_CATEGORY
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventCategoryFactory,
	EventVenueFactory,
	UserFactory,
)
from buzz.utils import is_app_installed


class TestCreateEvent(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Event Category", DEFAULT_CATEGORY):
			EventCategoryFactory.create(name=DEFAULT_CATEGORY)
		cls.owner = UserFactory.create_once("create-event-owner@example.com").name
		cls.viewer = UserFactory.create_once("create-event-viewer@example.com").name
		cls.non_member = UserFactory.create_once("create-event-stranger@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")

	def setUp(self):
		self.enterContext(self.set_user(self.owner))

	def test_creates_an_event_the_team_owns(self):
		created = create_event(self.new_event(title="Frappeverse Mumbai"))

		event = frappe.get_doc("Buzz Event", created.name)
		self.assertEqual(created.title, "Frappeverse Mumbai")
		self.assertEqual(event.team, self.team)
		self.assertEqual(event.medium, "In Person")
		self.assertEqual(event.category, DEFAULT_CATEGORY)

	def test_carries_the_optional_fields_through(self):
		created = create_event(
			self.new_event(
				end_date=add_days(today(), 31), about="<p>Come along</p>", time_zone="Asia/Kolkata"
			)
		)

		event = frappe.get_doc("Buzz Event", created.name)
		self.assertEqual(event.about, "<p>Come along</p>")
		self.assertEqual(event.time_zone, "Asia/Kolkata")
		# Derived on validate from the zone, so it proves the zone reached the document.
		self.assertEqual(event.time_zone_label, "IST")

	def test_a_viewer_cannot_create_events(self):
		with self.set_user(self.viewer), self.assertRaises(CannotCreateEvents):
			create_event(self.new_event())

	def test_a_non_member_cannot_create_events(self):
		with self.set_user(self.non_member), self.assertRaises(CannotCreateEvents):
			create_event(self.new_event())

	def test_zoom_is_refused_when_the_app_is_missing(self):
		if is_app_installed("zoom_integration"):
			self.skipTest("zoom_integration is installed on this site")

		with self.assertRaises(ZoomNotAvailable):
			create_event(self.new_event(zoom_meeting=True))

	def new_event(self, **overrides) -> NewEvent:
		values = {
			"team": self.team,
			"title": "Frappeverse Mumbai",
			"start_date": add_days(today(), 30),
			"start_time": "09:00:00",
			"end_time": "17:00:00",
		}
		return NewEvent(**values | overrides)


class TestGetEvent(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("get-event-owner@example.com").name
		cls.viewer = UserFactory.create_once("get-event-viewer@example.com").name
		cls.stranger = UserFactory.create_once("get-event-stranger@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")

	def test_returns_the_fields_the_manage_page_edits(self):
		event = self.create_team_event(
			short_description="A short one",
			about="<p>A long one</p>",
			medium="Online",
			meeting_link="https://example.com/join",
		)

		detail = self.detail_as(self.owner, event)

		self.assertEqual(detail["name"], event)
		self.assertEqual(detail["short_description"], "A short one")
		self.assertEqual(detail["about"], "<p>A long one</p>")
		self.assertEqual(detail["medium"], "Online")
		self.assertEqual(detail["meeting_link"], "https://example.com/join")
		self.assertIsNone(detail["venue"])
		self.assertTrue(detail["modified"])

	def test_resolves_the_venue_with_its_address(self):
		venue = EventVenueFactory.create(team=self.team, address="12 Example Street").name
		event = self.create_team_event("in_person", venue=venue)

		detail = self.detail_as(self.owner, event)

		self.assertEqual(detail["venue"]["name"], venue)
		self.assertEqual(detail["venue"]["address"], "12 Example Street")

	def test_a_viewer_cannot_open_the_manage_payload(self):
		event = self.create_team_event()

		with self.assertRaises(CannotManageEvent):
			self.detail_as(self.viewer, event)

	def test_a_non_member_cannot_open_the_manage_payload(self):
		event = self.create_team_event()

		with self.assertRaises(CannotManageEvent):
			self.detail_as(self.stranger, event)

	def test_an_unknown_event_is_not_found(self):
		with self.assertRaises(EventNotFound):
			self.detail_as(self.owner, "999999999")

	def create_team_event(self, *traits: str, **overrides) -> str:
		return str(BuzzEventFactory.create(*traits, team=self.team, **overrides).name)

	def detail_as(self, user: str, event: str) -> dict:
		with self.set_user(user):
			return get_event(event).__json__()
