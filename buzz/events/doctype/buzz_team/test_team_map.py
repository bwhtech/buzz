import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.events.doctype.buzz_team.team_page import TeamPage
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventVenueFactory


class TestTeamMap(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.team = BuzzTeamFactory.create_owned_by(team_name="Mapped Builders")
		cls.create_event("Mumbai Meetup", "India", latitude=19.07, longitude=72.87, city="Mumbai")
		cls.create_event("Pune Meetup", "India", latitude=18.52, longitude=73.86, city="Pune")
		cls.create_event("Arctic Meetup", "Svalbard and Jan Mayen", latitude=78.22, longitude=15.65)
		cls.create_event("Unmapped Meetup", "India")
		BuzzEventFactory.create(title="Online Meetup", team=cls.team.name, **cls.dates())

	@classmethod
	def dates(cls) -> dict:
		day = add_days(today(), 7)
		return {"start_date": day, "end_date": day}

	@classmethod
	def create_event(cls, title, country, **venue):
		venue = EventVenueFactory.create(team=cls.team.name, venue_country=country, **venue)
		BuzzEventFactory.create(
			title=title, team=cls.team.name, medium="In Person", venue=venue.name, **cls.dates()
		)

	def context(self) -> dict:
		return TeamPage(frappe.get_doc("Buzz Team", self.team.name)).as_context()

	def pinned_titles(self) -> set[str]:
		events = self.context()["page_data"]["upcoming"]
		return {event["title"] for event in events if event["latitude"] is not None}

	def test_only_venues_with_coordinates_are_pinned(self):
		self.assertEqual(self.pinned_titles(), {"Mumbai Meetup", "Pune Meetup", "Arctic Meetup"})

	def test_countries_count_upcoming_events(self):
		countries = self.context()["countries"]

		self.assertEqual(
			countries, [{"name": "India", "count": 3}, {"name": "Svalbard and Jan Mayen", "count": 1}]
		)

	def test_time_zones_cover_each_country_with_the_pytz_fallback(self):
		zones = self.context()["page_data"]["time_zone_countries"]

		self.assertEqual(zones["Asia/Kolkata"], "India")
		# Frappe's Country record for Svalbard lists no zones; pytz knows it.
		self.assertEqual(zones["Arctic/Longyearbyen"], "Svalbard and Jan Mayen")

	def test_the_map_needs_a_pin(self):
		team = BuzzTeamFactory.create_owned_by(team_name="Online Only Builders")

		context = TeamPage(team).as_context()

		self.assertFalse(context["has_pins"])
