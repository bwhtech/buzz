import json
import re
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response_content

from buzz.api.events.test_events import create_event
from buzz.api.forms.test_forms import ensure_event_host
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.www.event.index import EventPage
from buzz.www.event.venue_map import google_maps_url, open_street_map_url


def render(route: str) -> str:
	set_request(method="GET", path=f"/events/{route}")
	# CI never runs bench build, so there is no assets.json for bundled_asset to read
	with patch("frappe.utils.get_assets_json", return_value={}):
		return get_response_content(f"/events/{route}")


def structured_data(html: str) -> dict:
	match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
	return json.loads(match.group(1))


class TestEventPage(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		if not frappe.db.exists("Event Category", "Test Category"):
			frappe.get_doc({"doctype": "Event Category", "name": "Test Category"}).insert()
		owner = create_user("event-page-owner@example.com", "Owner")
		cls.team = create_owned_team("Event Page Team", owner)
		cls.event = create_event(
			"Public Page", cls.team, route="public-page-event", is_published=1, about="<p><b>Welcome</b></p>"
		)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_published_event_context(self):
		context = EventPage("public-page-event").as_context()
		self.assertEqual(str(context["event"].name), self.event)
		self.assertEqual([host.label for host in context["hosts"]], ["Event Page Team"])
		self.assertTrue(context["timezone_label"])

	def test_unpublished_event_is_not_found(self):
		create_event("Hidden Page", self.team, route="hidden-page-event", is_published=0)
		with self.assertRaises(frappe.PageDoesNotExistError):
			EventPage("hidden-page-event")

	def test_unknown_route_is_not_found(self):
		with self.assertRaises(frappe.PageDoesNotExistError):
			EventPage("no-such-event-route")

	def test_guest_sees_same_context(self):
		expected = EventPage("public-page-event").as_context()
		frappe.set_user("Guest")
		context = EventPage("public-page-event").as_context()
		self.assertEqual(context["hosts"], expected["hosts"])
		self.assertEqual(context["event_date"], expected["event_date"])

	def test_schedule_time_before_ten(self):
		event = frappe.get_doc(
			"Buzz Event", create_event("Schedule", self.team, route="schedule-page-event", is_published=1)
		)
		event.append(
			"schedule",
			{
				"type": "Break",
				"description": "Coffee",
				"date": event.start_date,
				"start_time": "09:00:00",
				"end_time": "09:30:00",
			},
		)
		event.flags.ignore_mandatory = True
		event.save()
		row = EventPage("schedule-page-event").as_context()["schedule"][0]["rows"][0]
		self.assertEqual(row["time"], "09:00 \u2013 09:30")
		self.assertEqual(row["title"], "Coffee")

	def test_schedule_talk_shows_title_and_speakers(self):
		event = frappe.get_doc(
			"Buzz Event", create_event("Talks", self.team, route="talks-page-event", is_published=1)
		)
		speaker = frappe.get_doc({"doctype": "Speaker Profile", "display_name": "Asha Rao"})
		speaker.insert(ignore_mandatory=True)
		talk = frappe.get_doc(
			{
				"doctype": "Event Talk",
				"title": "Scaling apps",
				"event": event.name,
				"submitted_by": "Administrator",
				"speakers": [{"speaker": speaker.name}],
			}
		).insert()
		event.append("featured_speakers", {"speaker": speaker.name})
		event.append(
			"schedule",
			{
				"type": "Talk",
				"talk": talk.name,
				"date": event.start_date,
				"start_time": "10:00:00",
				"end_time": "10:30:00",
			},
		)
		event.flags.ignore_mandatory = True
		event.save()
		context = EventPage("talks-page-event").as_context()
		row = context["schedule"][0]["rows"][0]
		self.assertEqual((row["title"], row["speakers"]), ("Scaling apps", "Asha Rao"))
		self.assertEqual(context["speakers"][0]["name"], "Asha Rao")

	def test_time_zone_falls_back_to_system(self):
		frappe.db.set_value("Buzz Event", self.event, {"time_zone": "", "time_zone_label": ""})
		self.assertTrue(EventPage("public-page-event").timezone_label)

	def test_team_hosts_first_then_co_hosts(self):
		event = frappe.get_doc(
			"Buzz Event", create_event("Hosts", self.team, route="hosts-page-event", is_published=1)
		)
		for name in ("Acme Page Host", "Beta Page Host"):
			event.append("co_hosts", {"host": ensure_event_host(name)})
		event.save()
		hosts = EventPage("hosts-page-event").as_context()["hosts"]
		self.assertEqual(
			[host.label for host in hosts], ["Event Page Team", "Acme Page Host", "Beta Page Host"]
		)

	def test_title_is_escaped(self):
		frappe.db.set_value("Buzz Event", self.event, "title", "<script>alert(1)</script>")
		html = render("public-page-event")
		self.assertNotIn("<script>alert(1)</script>", html)
		self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

	def test_about_markup_survives(self):
		self.assertIn("<b>Welcome</b>", render("public-page-event"))

	def test_event_theme_overrides_the_default(self):
		frappe.db.set_value("Buzz Event", self.event, "theme", "Paper")
		html = render("public-page-event")
		self.assertIn('data-mode="light"', html)
		# The theme CSS sits in an autoescaped <style>; a quoted selector would arrive as &#34;
		self.assertIn(":root[data-mode=dark] { color-scheme: dark; }", html)

	def test_additional_page(self):
		frappe.get_doc(
			{
				"doctype": "Additional Event Page",
				"event": self.event,
				"title": "Travel",
				"content": "<p>Trains</p>",
				"is_published": 1,
			}
		).insert()
		context = EventPage("public-page-event", "travel").as_context()
		self.assertEqual(context["page"].title, "Travel")
		self.assertEqual([page.route for page in context["pages"]], ["travel"])

	def test_unpublished_additional_page_is_not_found(self):
		frappe.get_doc(
			{
				"doctype": "Additional Event Page",
				"event": self.event,
				"title": "Draft",
				"route": "draft",
				"content": "x",
			}
		).insert()
		with self.assertRaises(frappe.PageDoesNotExistError):
			EventPage("public-page-event", "draft")

	def test_tabs_list_only_sections_with_content(self):
		tabs = EventPage("public-page-event").as_context()["tabs"]
		self.assertEqual([tab["key"] for tab in tabs], ["about"])

	def test_description_falls_back_to_about(self):
		frappe.db.set_value(
			"Buzz Event", self.event, {"short_description": "", "about": "<p>Tom &amp; Jerry " + "word " * 60}
		)
		description = EventPage("public-page-event").as_context()["meta"]["description"]
		self.assertTrue(description.startswith("Tom & Jerry word"))
		self.assertLessEqual(len(description), 160)

	def test_additional_page_title_names_both(self):
		frappe.get_doc(
			{
				"doctype": "Additional Event Page",
				"event": self.event,
				"title": "Venue",
				"content": "<p>Map</p>",
				"is_published": 1,
			}
		).insert()
		context = EventPage("public-page-event", "venue").as_context()
		self.assertEqual(context["meta"]["title"], f"Venue · {context['event'].title}")
		self.assertIsNone(context["structured_data"])

	def test_private_image_is_skipped(self):
		frappe.db.set_value(
			"Buzz Event",
			self.event,
			{"meta_image": "/private/files/meta.png", "banner_image": "/files/banner.png", "card_image": ""},
		)
		meta = EventPage("public-page-event").as_context()["meta"]
		self.assertTrue(meta["image"].endswith("/files/banner.png"))
		self.assertEqual(meta["card"], "summary_large_image")

	def test_no_image_uses_summary_card(self):
		frappe.db.set_value(
			"Buzz Event", self.event, {"meta_image": "", "banner_image": "", "card_image": ""}
		)
		meta = EventPage("public-page-event").as_context()["meta"]
		self.assertEqual((meta["image"], meta["card"]), ("", "summary"))

	def test_structured_data_in_page(self):
		frappe.db.set_value(
			"Buzz Event",
			self.event,
			{
				"medium": "In Person",
				"time_zone": "Asia/Kolkata",
				"start_time": "09:30:00",
				"end_time": "17:00:00",
			},
		)
		data = structured_data(render("public-page-event"))
		self.assertEqual(data["@type"], "Event")
		self.assertTrue(data["startDate"].endswith("T09:30:00+05:30"))
		self.assertEqual(data["organizer"]["name"], "Event Page Team")
		self.assertIn("OfflineEventAttendanceMode", data["eventAttendanceMode"])

	def test_structured_data_cannot_close_its_script(self):
		frappe.db.set_value("Buzz Event", self.event, "title", "Talks </script><b>x</b>")
		html = render("public-page-event")
		self.assertEqual(structured_data(html)["name"], "Talks </script><b>x</b>")
		self.assertEqual(html.count("</script><b>"), 0)

	def test_online_event_links_the_page_not_the_join_link(self):
		frappe.db.set_value("Buzz Event", self.event, "medium", "Online")
		data = EventPage("public-page-event").as_context()["structured_data"]
		self.assertEqual(data["location"], {"@type": "VirtualLocation", "url": data["url"]})

	def test_no_offer_when_registrations_are_closed(self):
		frappe.db.set_value("Buzz Event", self.event, "registrations_close_at", "2000-01-01 00:00:00")
		self.assertNotIn("offers", EventPage("public-page-event").as_context()["structured_data"])


class TestVenueMap(IntegrationTestCase):
	def test_google_embed_keeps_only_google_source(self):
		embed = '<iframe src="https://www.google.com/maps/embed?pb=abc" onload="alert(1)"></iframe>'
		self.assertEqual(google_maps_url(embed), "https://www.google.com/maps/embed?pb=abc")

	def test_google_embed_rejects_other_hosts(self):
		self.assertIsNone(google_maps_url('<iframe src="https://evil.example/maps/embed"></iframe>'))
		self.assertIsNone(google_maps_url('<iframe src="javascript:alert(1)"></iframe>'))
		self.assertIsNone(google_maps_url("http://www.google.com/maps/embed?pb=abc"))

	def test_open_street_map_needs_coordinates(self):
		self.assertIsNone(open_street_map_url(0, 0))
		self.assertIn("marker=19.0%2C72.8", open_street_map_url(19.0, 72.8))
