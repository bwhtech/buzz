import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.events.doctype.event_topic.topic_page import TopicPage
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventTopicFactory


def event_titles(days: list[dict]) -> list[str]:
	return [event["title"] for day in days for event in day["events"]]


class TestTopicPage(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.topic = EventTopicFactory.create(is_published=1)
		team = BuzzTeamFactory.create_owned_by(team_name="Topic Hosts")
		for title, offset in (("Upcoming Topic Meetup", 7), ("Past Topic Meetup", -30)):
			day = add_days(today(), offset)
			BuzzEventFactory.create(
				title=title, team=team.name, start_date=day, end_date=day, topics=[{"topic": cls.topic.name}]
			)
		BuzzEventFactory.create(title="Untagged Meetup", team=team.name, start_date=add_days(today(), 7))

	def context(self) -> dict:
		return TopicPage(frappe.get_doc("Event Topic", self.topic.name)).as_context()

	def test_upcoming_lists_only_the_topics_events(self):
		self.assertEqual(event_titles(self.context()["upcoming_days"]), ["Upcoming Topic Meetup"])

	def test_past_lists_only_the_topics_events(self):
		self.assertEqual(event_titles(self.context()["past_days"]), ["Past Topic Meetup"])
