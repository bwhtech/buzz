import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, format_date, getdate, today

from buzz.events.doctype.buzz_team.team_page import TeamPage, day_labels
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory


def event_titles(days: list[dict]) -> list[str]:
	return [event["title"] for day in days for event in day["events"]]


class TestTeamPage(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.team = BuzzTeamFactory.create_owned_by(team_name="Timeline Builders")
		cls.other_team = BuzzTeamFactory.create_owned_by(team_name="Elsewhere Builders")
		cls.create_event("Next Week Meetup", 7, start_time="18:30:00", end_time="20:00:00")
		cls.create_event("Last Month Meetup", -30)
		cls.create_event("Draft Meetup", 7, is_published=0)
		cls.create_event("Other Team Meetup", 7, team=cls.other_team.name)
		cls.create_event("Ended This Morning", 0, start_time="00:00:00", end_time="00:00:01")

	@classmethod
	def create_event(cls, title, offset, **overrides):
		day = add_days(today(), offset)
		attributes = {"title": title, "team": cls.team.name, "start_date": day, "end_date": day}
		return BuzzEventFactory.create(**(attributes | overrides))

	def context(self) -> dict:
		return TeamPage(frappe.get_doc("Buzz Team", self.team.name)).as_context()

	def test_upcoming_lists_only_the_teams_published_upcoming_events(self):
		titles = event_titles(self.context()["upcoming_days"])

		self.assertIn("Next Week Meetup", titles)
		self.assertNotIn("Draft Meetup", titles)
		self.assertNotIn("Other Team Meetup", titles)
		self.assertNotIn("Last Month Meetup", titles)

	def test_an_event_that_ended_today_moves_to_past(self):
		context = self.context()

		self.assertNotIn("Ended This Morning", event_titles(context["upcoming_days"]))
		self.assertIn("Ended This Morning", event_titles(context["past_days"]))

	def test_past_is_newest_first(self):
		titles = event_titles(self.context()["past_days"])

		self.assertLess(titles.index("Ended This Morning"), titles.index("Last Month Meetup"))

	def test_card_carries_time_host_and_place(self):
		card = next(
			event
			for day in self.context()["upcoming_days"]
			for event in day["events"]
			if event["title"] == "Next Week Meetup"
		)

		self.assertEqual(card["time"], "18:30")
		self.assertEqual(card["host_names"], "Timeline Builders")
		self.assertTrue(card["is_online"])
		self.assertTrue(card["url"].startswith("/events/"))

	def test_day_labels_are_relative_then_dates(self):
		self.assertEqual(day_labels(getdate(today()))["label"], "Today")
		self.assertEqual(day_labels(getdate(add_days(today(), 1)))["label"], "Tomorrow")
		later = getdate(add_days(today(), 5))
		self.assertEqual(day_labels(later)["label"], format_date(later, "d MMM"))
		self.assertEqual(day_labels(later)["weekday"], format_date(later, "EEEE"))

	def test_events_hosted_counts_published_events(self):
		self.assertEqual(self.context()["events_hosted"], 3)

	def test_links_drop_non_web_urls(self):
		team = frappe.get_doc("Buzz Team", self.team.name)
		team.set(
			"links",
			[
				{"icon": "globe", "label": "Site", "url": "https://example.com"},
				{"icon": "link", "label": "Sneaky", "url": "javascript:alert(1)"},
			],
		)

		labels = [link["label"] for link in TeamPage(team).as_context()["links"]]

		self.assertEqual(labels, ["Site"])
