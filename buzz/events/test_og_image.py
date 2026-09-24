import io
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from PIL import Image

from buzz.api.events.test_events import create_event
from buzz.events.banner_pattern import banner_pattern
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.events.doctype.buzz_theme.test_buzz_theme import copy_of_classic
from buzz.events.og_image import EventOgImage, generate, theme_colours
from buzz.www.event.index import EventPage


def og_files(event: str) -> list:
	return frappe.get_all(
		"File", filters={"attached_to_name": event, "attached_to_field": "og_image"}, pluck="file_url"
	)


class TestEventOgImage(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.team = create_owned_team("Og Image Team", create_user("og-image-owner@example.com", "Owner"))

	def setUp(self):
		self.event = create_event("Og Image", self.team, route="og-image-event", is_published=1)

	def tearDown(self):
		frappe.delete_doc("Buzz Event", self.event, force=True)

	def og_image(self) -> str:
		return frappe.db.get_value("Buzz Event", self.event, "og_image")

	def test_renders_a_share_sized_png(self):
		content = EventOgImage(frappe.get_doc("Buzz Event", self.event)).render()
		self.assertEqual(Image.open(io.BytesIO(content)).size, (1200, 630))

	def test_unchanged_event_keeps_its_image(self):
		generate(self.event)
		first = self.og_image()
		generate(self.event)
		self.assertEqual((self.og_image(), og_files(self.event)), (first, [first]))

	def test_changed_event_replaces_its_image(self):
		generate(self.event)
		first = self.og_image()
		frappe.db.set_value("Buzz Event", self.event, "title", "Renamed")
		generate(self.event)
		self.assertNotEqual(self.og_image(), first)
		self.assertEqual(og_files(self.event), [self.og_image()])

	def test_unpublished_event_is_not_rendered(self):
		frappe.db.set_value("Buzz Event", self.event, "is_published", 0)
		generate(self.event)
		self.assertIsNone(self.og_image())

	def test_undrawable_title_clears_the_image(self):
		generate(self.event)
		frappe.db.set_value("Buzz Event", self.event, "title", "फ्रैपे यात्रा")
		generate(self.event)
		self.assertIsNone(self.og_image())
		self.assertEqual(og_files(self.event), [])

	def test_saving_a_published_event_queues_a_render(self):
		event = frappe.get_doc("Buzz Event", self.event)
		with patch("frappe.in_test", False), patch("frappe.enqueue") as enqueue:
			event.save()
		self.assertEqual(enqueue.call_args.kwargs["event_name"], self.event)

	def test_event_page_shares_the_generated_image(self):
		frappe.db.set_value(
			"Buzz Event", self.event, {"meta_image": "", "banner_image": "", "card_image": ""}
		)
		generate(self.event)
		meta = EventPage("og-image-event").as_context()["meta"]
		self.assertTrue(meta["image"].endswith(self.og_image()))

	def test_transparent_banner_sits_on_the_page_colour(self):
		banner = io.BytesIO()
		Image.new("RGBA", (1200, 400), (0, 0, 0, 0)).save(banner, "PNG")
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "clear-banner.png",
				"is_private": 0,
				"content": banner.getvalue(),
			}
		).insert()
		frappe.db.set_value("Buzz Event", self.event, "banner_image", file.file_url)
		image = EventOgImage(frappe.get_doc("Buzz Event", self.event))
		corner = Image.open(io.BytesIO(image.render())).getpixel((0, 0))
		self.assertEqual("#%02x%02x%02x" % corner[:3], image.colours["page-bg"])

	def test_css_only_colour_falls_back_to_the_scheme(self):
		theme = copy_of_classic("Oklch Og Theme")
		row = next(row for row in theme.tokens if row.token == "page-bg")
		row.value = row.dark_value = "oklch(20% 0.02 250)"
		theme.insert()
		self.assertTrue(theme_colours(theme.name)["page-bg"].startswith("#"))


class TestBannerPattern(IntegrationTestCase):
	def test_matches_the_page_script(self):
		# Values produced by bannerPattern() in event_banner.ts
		expected = {
			"MangaloreFOSS 2026": (87, -2, 58, 61, 22.9),
			"Frappe Partner Meetup: Pune": (2, 2, 84, 93, 23.5),
			"Open Source Maintainer Summit": (105, 107, 73, 101, 22.5),
		}
		for title, values in expected.items():
			self.assertEqual(tuple(banner_pattern(title).values()), values, title)
