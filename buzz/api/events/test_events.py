import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today
from pydantic import ValidationError

from buzz.api.events import get_my_events
from buzz.events.doctype.buzz_team.test_buzz_team import payload_for
from buzz.test_permissions import create_ticket
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventTicketFactory,
	UserFactory,
)


class TestGetMyEvents(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.host_user = UserFactory.create_once("events-host@example.com").name
		cls.attendee = UserFactory.create_once("events-attendee@example.com").name
		cls.host_team = BuzzTeamFactory.create_owned_by(cls.host_user, team_name="My Events Host Team").name
		cls.other_team = BuzzTeamFactory.create_owned_by(cls.attendee).name

	def test_returns_unpublished_event_of_own_team_as_host(self):
		event = self.create_team_event(self.host_team, "unpublished")

		self.assertTrue(self.row_of(self.upcoming_of(self.host_user), event)["is_host"])

	def test_returns_ticketed_event_of_another_team_as_guest(self):
		event = self.create_team_event(self.host_team)
		self.submit_ticket(event, self.attendee)

		self.assertFalse(self.row_of(self.upcoming_of(self.attendee), event)["is_host"])

	def test_returns_hosted_and_ticketed_event_once_as_host(self):
		event = self.create_team_event(self.host_team)
		self.submit_ticket(event, self.host_user)

		upcoming = self.upcoming_of(self.host_user)

		self.assertEqual(self.names_in(upcoming).count(event), 1)
		self.assertTrue(self.row_of(upcoming, event)["is_host"])

	def test_ignores_a_draft_ticket(self):
		event = self.create_team_event(self.other_team)
		EventTicketFactory.create(event=event, attendee_email=self.host_user)

		self.assertNotIn(event, self.all_events_of(self.host_user))

	def test_excludes_another_teams_event_without_a_ticket(self):
		event = self.create_team_event(self.other_team, is_published=1)

		self.assertNotIn(event, self.all_events_of(self.host_user))

	def test_keeps_an_event_in_progress_upcoming(self):
		event = self.create_team_event(
			self.host_team, start_date=add_days(today(), -1), end_date=add_days(today(), 1)
		)

		events = self.events_of(self.host_user)

		self.assertIn(event, self.names_in(events["upcoming"]))
		self.assertNotIn(event, self.names_in(events["past"]))

	def test_moves_a_finished_event_to_past(self):
		event = self.create_team_event(
			self.host_team, start_date=add_days(today(), -3), end_date=add_days(today(), -1)
		)

		events = self.events_of(self.host_user)

		self.assertIn(event, self.names_in(events["past"]))
		self.assertNotIn(event, self.names_in(events["upcoming"]))

	def test_drops_hosted_events_once_the_membership_is_disabled(self):
		member = UserFactory.create_once("events-lapsed@example.com").name
		membership = BuzzTeamMembershipFactory.create(team=self.host_team, user=member, team_role="Manager")
		event = self.create_team_event(self.host_team)
		self.assertIn(event, self.names_in(self.upcoming_of(member)))

		frappe.db.set_value("Buzz Team Membership", membership.name, "enabled", 0)

		self.assertNotIn(event, self.names_in(self.upcoming_of(member)))

	def test_carries_the_organising_team(self):
		frappe.db.set_value("Buzz Team", self.host_team, "logo", "/files/team-logo.png")
		event = self.create_team_event(self.host_team)

		row = self.row_of(self.upcoming_of(self.host_user), event)

		self.assertEqual(row["team"], self.host_team)
		self.assertEqual(row["team_name"], "My Events Host Team")
		self.assertEqual(row["team_logo"], "/files/team-logo.png")

	def test_survives_an_event_with_no_team(self):
		event = self.create_team_event(self.host_team)
		frappe.db.set_value("Buzz Event", event, "team", None)
		self.submit_ticket(event, self.host_user)

		row = self.row_of(self.upcoming_of(self.host_user), event)

		self.assertIsNone(row["team"])
		self.assertIsNone(row["team_name"])
		self.assertIsNone(row["team_logo"])

	def test_a_role_filter_keeps_only_hosted_events(self):
		hosted, ticketed = self.hosted_and_ticketed()

		names = self.names_in(self.upcoming_of(self.host_user, role="hosting"))

		self.assertIn(hosted, names)
		self.assertNotIn(ticketed, names)

	def test_a_role_filter_keeps_only_ticketed_events(self):
		hosted, ticketed = self.hosted_and_ticketed()

		names = self.names_in(self.upcoming_of(self.host_user, role="attending"))

		self.assertIn(ticketed, names)
		self.assertNotIn(hosted, names)

	def test_a_team_filter_keeps_only_that_teams_events(self):
		hosted, ticketed = self.hosted_and_ticketed()

		names = self.names_in(self.upcoming_of(self.host_user, team=self.host_team))

		self.assertIn(hosted, names)
		self.assertNotIn(ticketed, names)

	def test_a_medium_filter_keeps_only_that_medium(self):
		online = self.create_team_event(self.host_team, medium="Online")
		in_person = self.create_team_event(self.host_team, "in_person")

		names = self.names_in(self.upcoming_of(self.host_user, medium="Online"))

		self.assertIn(online, names)
		self.assertNotIn(in_person, names)

	def test_an_unknown_filter_value_is_refused(self):
		with self.assertRaises(ValidationError):
			self.events_of(self.host_user, role="lurking")

	def hosted_and_ticketed(self) -> tuple[str, str]:
		"""One event the host's team runs, and one of another team the host holds a ticket to."""
		ticketed = self.create_team_event(self.other_team)
		self.submit_ticket(ticketed, self.host_user)
		return self.create_team_event(self.host_team), ticketed

	def events_of(self, user: str, **filters) -> dict[str, list[dict]]:
		with self.set_user(user):
			return get_my_events(filters or None).__json__()

	def upcoming_of(self, user: str, **filters) -> list[dict]:
		return self.events_of(user, **filters)["upcoming"]

	def all_events_of(self, user: str) -> list[str]:
		events = self.events_of(user)
		return self.names_in(events["upcoming"] + events["past"])

	def row_of(self, events: list[dict], event: str) -> dict:
		rows = [row for row in events if row["name"] == event]
		self.assertEqual(len(rows), 1)
		return rows[0]

	def create_team_event(self, team: str, *traits: str, **overrides) -> str:
		return str(BuzzEventFactory.create(*traits, team=team, **overrides).name)

	def submit_ticket(self, event: str, email: str):
		EventTicketFactory.create("submitted", event=event, attendee_email=email)

	def names_in(self, events: list[dict]) -> list[str]:
		return [event["name"] for event in events]


# Kept for modules that still import them. The cleanup PR deletes them.
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
