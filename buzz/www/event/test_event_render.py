import json
import re
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response_content

from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, UserFactory
from buzz.www.event.index import EventPage
from buzz.www.site_header import DEFAULT_FAVICON


class TestEventPageRender(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		owner = UserFactory.create_once("event-page-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(owner, team_name="Event Page Team").name
		event = BuzzEventFactory.create(team=cls.team, about="<p><b>Welcome</b></p>")
		cls.event, cls.route = str(event.name), event.route

	def test_links_render_with_a_fallback_icon(self):
		event = frappe.get_doc("Buzz Event", BuzzEventFactory.create(team=self.team).name)
		event.append("external_links", {"icon": "unknown", "label": "Join the chat", "url": "https://t.me/x"})
		event.save()

		html = render(event.route)

		self.assertIn('href="https://t.me/x"', html)
		self.assertIn("Join the chat", html)
		self.assertIn("M10 13a5", html)

	def test_title_is_escaped(self):
		self.set_event({"title": "<script>alert(1)</script>"})
		html = render(self.route)
		self.assertNotIn("<script>alert(1)</script>", html)
		self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

	def test_about_markup_survives(self):
		self.assertIn("<b>Welcome</b>", render(self.route))

	def test_event_theme_overrides_the_default(self):
		self.set_event({"theme": "Paper"})
		html = render(self.route)
		self.assertIn('defaultMode = "light"', html)
		# The theme CSS sits in an autoescaped <style>; a quoted selector would arrive as &#34;
		self.assertIn(":root[data-mode=dark] { color-scheme: dark; }", html)

	def test_title_tag_is_escaped(self):
		self.set_event({"title": "&lt;script&gt;alert(1)&lt;/script&gt;"})
		title = re.search(r"<title>(.*?)</title>", render(self.route), re.DOTALL).group(1)
		self.assertIn("&amp;lt;script&amp;gt;", title)

	def test_page_skips_frappe_website_assets(self):
		html = render(self.route)
		for asset in ("website.bundle", "frappe-web.bundle", "icons/lucide"):
			self.assertNotIn(asset, html)
		self.assertEqual(html.count('property="og:title"'), 1)

	def test_favicon_falls_back_to_buzz(self):
		settings = frappe.get_single("Website Settings")
		self.addCleanup(frappe.clear_document_cache, "Website Settings", "Website Settings")
		self.addCleanup(settings.db_set, "favicon", settings.favicon)
		settings.db_set("favicon", None)
		frappe.clear_document_cache("Website Settings", "Website Settings")
		self.assertIn(DEFAULT_FAVICON, render(self.route))

	def test_structured_data_in_page(self):
		times = {"time_zone": "Asia/Kolkata", "start_time": "09:30:00", "end_time": "17:00:00"}
		self.set_event({"medium": "In Person", **times})
		data = structured_data(render(self.route))
		self.assertEqual(data["@type"], "Event")
		self.assertTrue(data["startDate"].endswith("T09:30:00+05:30"))
		self.assertEqual(data["organizer"]["name"], "Event Page Team")
		self.assertIn("OfflineEventAttendanceMode", data["eventAttendanceMode"])

	def test_structured_data_cannot_close_its_script(self):
		self.set_event({"title": "Talks </script><b>x</b>"})
		html = render(self.route)
		self.assertEqual(structured_data(html)["name"], "Talks </script><b>x</b>")
		self.assertEqual(html.count("</script><b>"), 0)

	def test_online_event_names_the_platform_but_never_shows_the_link(self):
		self.set_event({"medium": "Online", "meeting_link": "https://us02web.zoom.us/j/123?pwd=secret"})

		self.assertEqual(EventPage(self.route).as_context()["online_label"], "Online on Zoom")
		self.assertNotIn("zoom.us", render(self.route))

		self.set_event({"meeting_link": "https://notzoom.us.example/j/1"})
		self.assertEqual(EventPage(self.route).as_context()["online_label"], "Online")

	def test_upcoming_event_renders_a_countdown(self):
		self.set_event({"time_zone": "Asia/Kolkata", "start_date": "2099-01-05", "start_time": "09:30:00"})
		html = render(self.route)
		self.assertIn('starts-at="2099-01-05T09:30:00+05:30"', html)

	def test_ended_event_has_no_countdown(self):
		self.set_event({"start_date": "2020-01-05", "end_date": "2020-01-05"})
		self.assertNotIn("<event-countdown", render(self.route))

	def test_event_without_end_time_counts_to_end_of_last_day(self):
		self.set_event(
			{"time_zone": "UTC", "start_date": "2099-01-05", "end_date": "2099-01-06", "end_time": None}
		)
		countdown = EventPage(self.route).as_context()["countdown"]
		self.assertEqual(countdown["ends_at"], "2099-01-06T23:59:59+00:00")

	def set_event(self, values: dict):
		frappe.db.set_value("Buzz Event", self.event, values)


def render(route: str) -> str:
	set_request(method="GET", path=f"/events/{route}")
	# CI never runs bench build, so there is no assets.json for bundled_asset to read
	with patch("frappe.utils.get_assets_json", return_value={}):
		return get_response_content(f"/events/{route}")


def structured_data(html: str) -> dict:
	match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
	return json.loads(match.group(1))
