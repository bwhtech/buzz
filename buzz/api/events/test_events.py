import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.events import get_my_events
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user, payload_for
from buzz.test_permissions import add_member, create_ticket


def create_event(title: str, team: str, **overrides) -> str:
	payload = payload_for("Buzz Event", title) | {
		"start_date": add_days(today(), 30),
		"end_date": add_days(today(), 31),
	}
	event = frappe.get_doc({**payload, "team": team, **overrides}).insert(ignore_permissions=True)
	return str(event.name)


def issue_ticket(event: str, user: str) -> str:
	"""The booking flow submits every ticket it generates; the fixture stops at insert."""
	ticket = create_ticket(event, user)
	frappe.get_doc("Event Ticket", ticket).submit()
	return ticket


class TestGetMyEvents(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		if not frappe.db.exists("Event Category", "Test Category"):
			frappe.get_doc({"doctype": "Event Category", "name": "Test Category"}).insert(
				ignore_permissions=True
			)
		if not frappe.db.exists("Event Host", "Test Host"):
			frappe.get_doc({"doctype": "Event Host", "name": "Test Host"}).insert(ignore_permissions=True)

		cls.host_user = create_user("events-host@example.com", "Host")
		cls.attendee = create_user("events-attendee@example.com", "Attendee")
		cls.host_team = create_owned_team("My Events Host Team", cls.host_user)
		cls.other_team = create_owned_team("My Events Other Team", cls.attendee)

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def events_of(self, user: str) -> dict[str, list[dict]]:
		frappe.set_user(user)
		return get_my_events().__json__()

	def names_in(self, events: list[dict]) -> list[str]:
		return [event["name"] for event in events]

	def test_returns_unpublished_event_of_own_team_as_host(self):
		event = create_event("Own Draft", self.host_team, is_published=0)

		upcoming = self.events_of(self.host_user)["upcoming"]

		self.assertIn(event, self.names_in(upcoming))
		self.assertTrue(next(row for row in upcoming if row["name"] == event)["is_host"])

	def test_returns_ticketed_event_of_another_team_as_guest(self):
		event = create_event("Ticketed Elsewhere", self.host_team)
		issue_ticket(event, self.attendee)

		upcoming = self.events_of(self.attendee)["upcoming"]

		self.assertIn(event, self.names_in(upcoming))
		self.assertFalse(next(row for row in upcoming if row["name"] == event)["is_host"])

	def test_returns_hosted_and_ticketed_event_once_as_host(self):
		event = create_event("Hosting And Attending", self.host_team)
		issue_ticket(event, self.host_user)

		upcoming = self.events_of(self.host_user)["upcoming"]

		self.assertEqual(self.names_in(upcoming).count(event), 1)
		self.assertTrue(next(row for row in upcoming if row["name"] == event)["is_host"])

	def test_ignores_a_draft_ticket(self):
		event = create_event("Never Booked", self.other_team)
		create_ticket(event, self.host_user)

		events = self.events_of(self.host_user)

		self.assertNotIn(event, self.names_in(events["upcoming"] + events["past"]))

	def test_excludes_another_teams_event_without_a_ticket(self):
		event = create_event("Someone Elses", self.other_team, is_published=1)

		events = self.events_of(self.host_user)

		self.assertNotIn(event, self.names_in(events["upcoming"] + events["past"]))

	def test_keeps_an_event_in_progress_upcoming(self):
		event = create_event(
			"Still Running",
			self.host_team,
			start_date=add_days(today(), -1),
			end_date=add_days(today(), 1),
		)

		events = self.events_of(self.host_user)

		self.assertIn(event, self.names_in(events["upcoming"]))
		self.assertNotIn(event, self.names_in(events["past"]))

	def test_moves_a_finished_event_to_past(self):
		event = create_event(
			"Wrapped Up",
			self.host_team,
			start_date=add_days(today(), -3),
			end_date=add_days(today(), -1),
		)

		events = self.events_of(self.host_user)

		self.assertIn(event, self.names_in(events["past"]))
		self.assertNotIn(event, self.names_in(events["upcoming"]))

	def test_drops_hosted_events_once_the_membership_is_disabled(self):
		member = create_user("events-lapsed@example.com", "Lapsed")
		membership = add_member(self.host_team, member, "Manager")
		event = create_event("Lapsed Access", self.host_team)
		self.assertIn(event, self.names_in(self.events_of(member)["upcoming"]))

		frappe.set_user("Administrator")
		frappe.db.set_value("Buzz Team Membership", membership, "enabled", 0)

		self.assertNotIn(event, self.names_in(self.events_of(member)["upcoming"]))

	def test_carries_the_organising_team(self):
		frappe.db.set_value("Buzz Team", self.host_team, "logo", "/files/team-logo.png")
		event = create_event("Team Stamped", self.host_team)

		row = next(row for row in self.events_of(self.host_user)["upcoming"] if row["name"] == event)

		self.assertEqual(row["team"], self.host_team)
		self.assertEqual(row["team_name"], "My Events Host Team")
		self.assertEqual(row["team_logo"], "/files/team-logo.png")

	def test_survives_an_event_with_no_team(self):
		event = create_event("Unstamped", self.host_team)
		frappe.db.set_value("Buzz Event", event, "team", None)
		ticket = issue_ticket(event, self.host_user)
		self.assertTrue(ticket)

		row = next(row for row in self.events_of(self.host_user)["upcoming"] if row["name"] == event)

		self.assertIsNone(row["team"])
		self.assertIsNone(row["team_name"])
		self.assertIsNone(row["team_logo"])

	def test_serializes_every_declared_field(self):
		create_event("Payload Shape", self.host_team)

		event = self.events_of(self.host_user)["upcoming"][0]

		self.assertEqual(
			set(event),
			{
				"name",
				"title",
				"route",
				"start_date",
				"end_date",
				"start_time",
				"end_time",
				"venue",
				"medium",
				"banner_image",
				"is_published",
				"is_host",
				"team",
				"team_name",
				"team_logo",
			},
		)
