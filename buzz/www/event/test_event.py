import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.events.doctype.buzz_team.buzz_team import create_personal_team_for
from buzz.tests.factories import (
	AdditionalEventPageFactory,
	BuzzEventFactory,
	BuzzFormFactory,
	BuzzScheduleFactory,
	BuzzScheduleTrackFactory,
	BuzzTeamFactory,
	EventHostFactory,
	EventTalkFactory,
	SpeakerProfileFactory,
	UserFactory,
)
from buzz.www.event.date_range import format_day, join_parts
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
		save_schedule(
			event, {"type": "Break", "title": "Coffee", "start_time": "09:00:00", "end_time": "09:30:00"}
		)
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
		event.save()
		row = {"type": "Talk", "reference_doctype": "Event Talk", "reference_document": talk.name}
		save_schedule(event, {**row, "start_time": "10:00:00", "end_time": "10:30:00"})
		context = EventPage(event.route).as_context()
		row = context["schedule"][0]["rows"][0]
		self.assertEqual((row["title"], row["speakers"]), ("Scaling apps", "Asha Rao"))
		self.assertEqual(context["speakers"][0]["name"], "Asha Rao")

	def test_unpublished_schedule_is_hidden(self):
		event = self.create_event()
		save_schedule(
			event, {"type": "Break", "start_time": "09:00:00", "end_time": "09:30:00"}, is_published=0
		)
		self.assertEqual(EventPage(event.route).as_context()["schedule"], [])

	def test_schedule_days_follow_their_order_and_labels(self):
		event = self.create_event()
		next_day = add_days(event.start_date, 1)
		days = [{"date": next_day, "label": "Workshops"}, {"date": event.start_date, "label": ""}]
		save_schedule(event, {"type": "Break", "start_time": "09:00:00", "end_time": "09:30:00"}, days=days)
		save_schedule(
			event, {"date": next_day, "type": "Workshop", "start_time": "09:00:00", "end_time": "10:00:00"}
		)
		labels = [day["day"] for day in EventPage(event.route).as_context()["schedule"]]
		self.assertEqual(labels, ["Workshops", format_day(event.start_date)])

	def test_join_parts_strips_spaces_around_each_part(self):
		self.assertEqual(join_parts(["Engineer ", " Frappe"], ", "), "Engineer, Frappe")
		self.assertEqual(join_parts(["  ", "Frappe"], ", "), "Frappe")

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

	def test_schedule_tab_links_to_the_schedule_page(self):
		event = self.create_event()
		save_schedule(event, {"type": "Break", "start_time": "09:00:00", "end_time": "09:30:00"})
		tabs = {tab["key"]: tab for tab in EventPage(event.route).as_context()["tabs"]}
		self.assertEqual(tabs["schedule"]["url"], f"/events/{event.route}/schedule")
		self.assertNotIn("url", tabs["about"])

	def test_schedule_groups_parallel_sessions_and_keeps_all_room_rows_alone(self):
		event = self.create_event()
		schedule = BuzzScheduleFactory.create(event=str(event.name), is_published=1)
		rooms = [BuzzScheduleTrackFactory.create(schedule=schedule.name).name for _ in range(2)]
		schedule.reload()
		times = {"start_time": "10:00:00", "end_time": "11:00:00", "date": event.start_date}
		for track in rooms:
			schedule.append("items", {**times, "type": "Talk", "title": "Parallel", "track": track})
		schedule.append("items", {**times, "type": "Break", "title": "Coffee", "all_tracks": 1})
		schedule.save()
		day = EventPage(event.route).as_context()["schedule"][0]
		self.assertEqual([len(slot["rows"]) for slot in day["slots"]], [1, 2])
		self.assertEqual(day["slots"][0]["rows"][0]["room_key"], "")
		self.assertTrue(all(row["room"] for row in day["slots"][1]["rows"]))

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
		BuzzFormFactory.set_registration_cutoff(self.event, f"{add_days(today(), -30)} 00:00:00")
		self.assertNotIn("offers", self.context()["structured_data"])

	def set_event(self, values: dict):
		frappe.db.set_value("Buzz Event", self.event, values)

	def context(self) -> dict:
		return EventPage(self.route).as_context()

	def create_event(self, **overrides):
		"""Read back, so the tests edit a plain document rather than the factory's subclass."""
		return frappe.get_doc("Buzz Event", BuzzEventFactory.create(team=self.team, **overrides).name)


def save_schedule(event, row: dict, **schedule_values):
	"""Add `row` to the event's schedule, creating a published one on first use."""
	name = frappe.db.get_value("Buzz Schedule", {"event": event.name})
	schedule = frappe.get_doc("Buzz Schedule", name) if name else None
	if not schedule:
		schedule = BuzzScheduleFactory.create(event=str(event.name), **{"is_published": 1, **schedule_values})
	schedule.append("items", {"date": event.start_date, "all_tracks": 1, **row})
	schedule.save()
