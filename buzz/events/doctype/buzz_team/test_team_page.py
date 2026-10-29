import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, format_date, getdate, today

from buzz.events.doctype.buzz_team.team_page import TeamPage, day_labels
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzFormFactory,
	BuzzTeamFactory,
	CommunityEventRequestFactory,
)


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

	def test_card_says_whether_registrations_are_closed(self):
		# Its own team, so the counts the other tests read stay put.
		team = BuzzTeamFactory.create_owned_by().name
		open_event = self.create_event("Open Meetup", 8, team=team)
		BuzzFormFactory.set_registration_cutoff(open_event.name, None)
		self.create_event("Closed Meetup", 8, team=team)
		days = TeamPage(frappe.get_doc("Buzz Team", team)).as_context()["upcoming_days"]
		cards = {event["title"]: event for day in days for event in day["events"]}

		self.assertFalse(cards["Open Meetup"]["registrations_closed"])
		self.assertTrue(cards["Closed Meetup"]["registrations_closed"])

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


def create_request(community: str, title: str, offset: int, *traits, **overrides):
	day = add_days(today(), offset)
	attributes = {
		"community": community,
		"event_title": title,
		"start_datetime": f"{day} 18:00:00",
		"end_datetime": f"{day} 20:00:00",
	}
	return CommunityEventRequestFactory.create(*traits, **(attributes | overrides))


class TestTeamPageExternalEvents(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.community = BuzzTeamFactory.create_owned_by(None, "community", team_name="External Builders")
		community = cls.community.name
		create_request(community, "Rust Meetup", 5, "approved", event_url="https://example.com/rust")
		create_request(community, "Pending Meetup", 5)
		create_request(community, "Rejected Meetup", 5, status="Rejected")
		create_request(community, "Ended Meetup", -3, "approved")
		day = add_days(today(), 2)
		BuzzEventFactory.create(title="Own Meetup", team=community, start_date=day, end_date=day)

	def context(self, team: str | None = None) -> dict:
		return TeamPage(frappe.get_doc("Buzz Team", team or self.community.name)).as_context()

	def test_an_approved_external_event_is_upcoming_in_date_order(self):
		titles = event_titles(self.context()["upcoming_days"])

		self.assertLess(titles.index("Own Meetup"), titles.index("Rust Meetup"))
		self.assertNotIn("Pending Meetup", titles)
		self.assertNotIn("Rejected Meetup", titles)

	def test_an_external_card_links_out_and_stays_off_the_map(self):
		days = self.context()["upcoming_days"]
		card = next(event for day in days for event in day["events"] if event["title"] == "Rust Meetup")

		self.assertEqual(card["url"], "https://example.com/rust")
		self.assertTrue(card["is_external"])
		self.assertIsNone(card["latitude"])
		self.assertEqual(card["time"], "18:00")

	def card_titled(self, title: str) -> dict:
		days = self.context()["upcoming_days"]
		return next(event for day in days for event in day["events"] if event["title"] == title)

	def test_an_external_event_with_one_coordinate_is_not_pinned(self):
		create_request(self.community.name, "Half Pinned Meetup", 6, "approved", latitude=18.5204)
		card = self.card_titled("Half Pinned Meetup")

		self.assertIsNone(card["latitude"])
		self.assertIsNone(card["longitude"])

	def test_an_external_event_with_zero_coordinates_is_not_pinned(self):
		create_request(self.community.name, "Zero Meetup", 6, "approved", latitude=0, longitude=0)
		card = self.card_titled("Zero Meetup")

		self.assertIsNone(card["latitude"])
		self.assertIsNone(card["longitude"])

	def test_an_external_event_with_coordinates_is_pinned(self):
		create_request(
			self.community.name,
			"Pinned Meetup",
			6,
			"approved",
			latitude=18.5204,
			longitude=73.8567,
			city="Pune",
		)
		card = self.card_titled("Pinned Meetup")

		self.assertEqual((card["latitude"], card["longitude"], card["city"]), (18.5204, 73.8567, "Pune"))
		self.assertTrue(self.context()["has_pins"])

	def test_an_ended_external_event_is_past(self):
		context = self.context()

		self.assertIn("Ended Meetup", event_titles(context["past_days"]))
		self.assertNotIn("Ended Meetup", event_titles(context["upcoming_days"]))

	def test_events_hosted_counts_only_own_events(self):
		self.assertEqual(self.context()["events_hosted"], 1)

	def test_a_team_not_accepting_submissions_hides_external_events(self):
		team = BuzzTeamFactory.create_owned_by(None, "community")
		create_request(team.name, "Closed Meetup", 5, "approved")
		team.db_set("accept_community_submissions", 0)

		self.assertNotIn("Closed Meetup", event_titles(self.context(team.name)["upcoming_days"]))
