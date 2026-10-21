import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.events.doctype.buzz_team.buzz_team import create_personal_team_for
from buzz.tests.factories import (
	AdditionalEventPageFactory,
	BuzzEventFactory,
	BuzzTeamFactory,
	EventHostFactory,
	EventTalkFactory,
	SpeakerProfileFactory,
	UserFactory,
)
from buzz.www.event.index import EventPage


class TestEventPage(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		owner = UserFactory.create_once("event-page-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(owner, team_name="Event Page Team").name
		event = BuzzEventFactory.create(team=cls.team, about="<p><b>Welcome</b></p>")
		cls.event, cls.route = str(event.name), event.route

	def test_published_event_context(self):
		context = self.context()
		self.assertEqual(str(context["event"].name), self.event)
		self.assertEqual([host.label for host in context["hosts"]], ["Event Page Team"])
		self.assertTrue(context["timezone_label"])

	def test_unpublished_event_is_not_found(self):
		route = self.create_event(is_published=0).route
		with self.assertRaises(frappe.PageDoesNotExistError):
			EventPage(route)

	def test_unknown_route_is_not_found(self):
		with self.assertRaises(frappe.PageDoesNotExistError):
			EventPage("no-such-event-route")

	def test_guest_sees_same_context(self):
		expected = self.context()
		with self.set_user("Guest"):
			context = self.context()
		self.assertEqual(context["hosts"], expected["hosts"])
		self.assertEqual(context["event_date"], expected["event_date"])

	def test_schedule_time_before_ten(self):
		event = self.create_event(start_time="08:00:00")
		schedule = {
			"type": "Break",
			"description": "Coffee",
			"start_time": "09:00:00",
			"end_time": "09:30:00",
		}
		save_schedule(event, schedule)
		row = EventPage(event.route).as_context()["schedule"][0]["rows"][0]
		self.assertEqual(row["time"], "09:00 \u2013 09:30")
		self.assertEqual(row["title"], "Coffee")

	def test_schedule_talk_shows_title_and_speakers(self):
		event = self.create_event()
		speaker_user = UserFactory.create(first_name="Asha", last_name="Rao").name
		speaker = SpeakerProfileFactory.create(user=speaker_user).name
		talk = EventTalkFactory.create(
			event=event.name, title="Scaling apps", speakers=[{"speaker": speaker}]
		)
		event.append("featured_speakers", {"speaker": speaker})
		save_schedule(
			event, {"type": "Talk", "talk": talk.name, "start_time": "10:00:00", "end_time": "10:30:00"}
		)
		context = EventPage(event.route).as_context()
		row = context["schedule"][0]["rows"][0]
		self.assertEqual((row["title"], row["speakers"]), ("Scaling apps", "Asha Rao"))
		self.assertEqual(context["speakers"][0]["name"], "Asha Rao")

	def test_time_zone_falls_back_to_system(self):
		self.set_event({"time_zone": "", "time_zone_label": ""})
		self.assertTrue(EventPage(self.route).timezone_label)

	def test_team_hosts_first_then_co_hosts(self):
		event = self.create_event()
		for name in ("Acme Page Host", "Beta Page Host"):
			event.append("co_hosts", {"host": EventHostFactory.create(team=self.team, host_name=name).name})
		event.save()
		hosts = EventPage(event.route).as_context()["hosts"]
		self.assertEqual(
			[host.label for host in hosts], ["Event Page Team", "Acme Page Host", "Beta Page Host"]
		)

	def test_personal_team_is_hosted_by_its_owner(self):
		user = UserFactory.create(first_name="Mira", last_name="Host", user_image="/files/mira.png").name
		team = create_personal_team_for(user).name
		event = BuzzEventFactory.create(team=team)

		with self.change_settings("Buzz Settings", enable_personal_teams=1):
			host = EventPage(event.route).as_context()["hosts"][0]

		username = frappe.db.get_value("User", user, "username")
		self.assertEqual(
			(host.label, host.logo, host.url), ("Mira Host", "/files/mira.png", f"/u/{username}")
		)

	def test_personal_host_is_not_linked_while_personal_teams_are_off(self):
		team = create_personal_team_for(UserFactory.create().name).name
		event = BuzzEventFactory.create(team=team)

		with self.change_settings("Buzz Settings", enable_personal_teams=0):
			host = EventPage(event.route).as_context()["hosts"][0]

		self.assertIsNone(host.url)

	def test_links_keep_table_order_and_drop_unsafe_urls(self):
		event = self.create_event()
		event.append(
			"external_links", {"icon": "map-pin", "label": "Venue map", "url": "https://maps.example.com"}
		)
		event.append("external_links", {"label": "Slides", "url": "https://slides.example.com"})
		event.save()
		frappe.db.set_value("Event External Link", event.external_links[1].name, "url", "javascript:alert(1)")

		links = EventPage(event.route).as_context()["links"]

		self.assertEqual([link["label"] for link in links], ["Venue map"])
		self.assertIn("M20 10c0", links[0]["icon_svg"])

	def test_additional_page_is_listed_with_its_content(self):
		# A fresh event: the class shares one event and rolls back per class, so pages
		# another test created would otherwise sit in this list too.
		event = self.create_event()
		page = AdditionalEventPageFactory.create(
			event=event.name, title="Travel", content="<p>Trains</p>", is_published=1
		)
		pages = EventPage(event.route).as_context()["pages"]
		self.assertEqual([(row["key"], row["label"]) for row in pages], [(page.name, "Travel")])
		self.assertIn("Trains", pages[0]["content"])

	def test_unpublished_additional_page_is_hidden(self):
		event = self.create_event()
		AdditionalEventPageFactory.create(event=event.name, title="Draft")
		self.assertEqual(EventPage(event.route).as_context()["pages"], [])

	def test_additional_pages_are_tabbed_in_display_order(self):
		event = self.create_event()
		AdditionalEventPageFactory.create(event=event.name, title="Travel", is_published=1, display_order=2)
		AdditionalEventPageFactory.create(
			event=event.name, title="Code of conduct", is_published=1, display_order=1
		)
		pages = EventPage(event.route).as_context()["pages"]
		self.assertEqual([row["label"] for row in pages], ["Code of conduct", "Travel"])

	def test_tabs_list_only_sections_with_content(self):
		self.assertEqual([tab["key"] for tab in self.context()["tabs"]], ["about"])

	def test_description_falls_back_to_about(self):
		self.set_event({"short_description": "", "about": "<p>Tom &amp; Jerry " + "word " * 60})
		description = self.context()["meta"]["description"]
		self.assertTrue(description.startswith("Tom & Jerry word"))
		self.assertLessEqual(len(description), 160)

	def test_private_image_is_skipped(self):
		self.set_event(
			{"meta_image": "/private/files/meta.png", "banner_image": "/files/banner.png", "card_image": ""}
		)
		meta = self.context()["meta"]
		self.assertTrue(meta["image"].endswith("/files/banner.png"))
		self.assertEqual(meta["card"], "summary_large_image")

	def test_no_image_uses_summary_card(self):
		self.set_event({"meta_image": "", "banner_image": "", "card_image": ""})
		meta = self.context()["meta"]
		self.assertEqual((meta["image"], meta["card"]), ("", "summary"))

	def test_online_event_links_the_page_not_the_join_link(self):
		self.set_event({"medium": "Online"})
		data = self.context()["structured_data"]
		self.assertEqual(data["location"], {"@type": "VirtualLocation", "url": data["url"]})

	def test_no_offer_when_registrations_are_closed(self):
		self.set_event({"registrations_close_at": f"{add_days(today(), -30)} 00:00:00"})
		self.assertNotIn("offers", self.context()["structured_data"])

	def set_event(self, values: dict):
		frappe.db.set_value("Buzz Event", self.event, values)

	def context(self) -> dict:
		return EventPage(self.route).as_context()

	def create_event(self, **overrides):
		"""Read back, so the tests edit a plain document rather than the factory's subclass."""
		return frappe.get_doc("Buzz Event", BuzzEventFactory.create(team=self.team, **overrides).name)


def save_schedule(event, row: dict):
	event.append("schedule", {"date": event.start_date, **row})
	event.flags.ignore_mandatory = True
	event.save()
