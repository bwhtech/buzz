import io
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from PIL import Image

from buzz.events.banner_pattern import banner_pattern
from buzz.events.og_image import EventOgImage, generate, theme_colours
from buzz.tests.factories import BuzzEventFactory, FileFactory
from buzz.tests.factories.events.buzz_theme_factory import BuzzThemeFactory
from buzz.www.event.index import EventPage


class TestEventOgImage(IntegrationTestCase):
	def setUp(self):
		self.event = str(BuzzEventFactory.create().name)

	def tearDown(self):
		# Removes the rendered files from disk too, which a rollback leaves behind
		frappe.delete_doc("Buzz Event", self.event, force=True)

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

	def test_emoji_title_is_rendered_in_colour(self):
		frappe.db.set_value("Buzz Event", self.event, "title", "👀")
		generate(self.event)
		self.assertTrue(self.og_image())
		image = EventOgImage(frappe.get_doc("Buzz Event", self.event))
		title_row = Image.open(io.BytesIO(image.render())).crop((64, 470, 140, 530))
		self.assertGreater(len(title_row.getcolors(maxcolors=100000)), 50)

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
		route = frappe.db.get_value("Buzz Event", self.event, "route")
		meta = EventPage(route).as_context()["meta"]
		self.assertTrue(meta["image"].endswith(self.og_image()))

	def test_transparent_banner_sits_on_the_page_colour(self):
		banner = io.BytesIO()
		Image.new("RGBA", (1200, 400), (0, 0, 0, 0)).save(banner, "PNG")
		file = FileFactory.create(file_name="clear-banner.png", content=banner.getvalue())
		frappe.db.set_value("Buzz Event", self.event, "banner_image", file.file_url)
		image = EventOgImage(frappe.get_doc("Buzz Event", self.event))
		corner = Image.open(io.BytesIO(image.render())).getpixel((0, 0))
		self.assertEqual("#%02x%02x%02x" % corner[:3], image.colours["page-bg"])

	def test_css_only_colour_falls_back_to_the_scheme(self):
		theme = BuzzThemeFactory.build()
		row = next(row for row in theme.tokens if row.token == "page-bg")
		row.value = row.dark_value = "oklch(20% 0.02 250)"
		theme.insert()
		self.assertTrue(theme_colours(theme.name)["page-bg"].startswith("#"))

	def og_image(self) -> str:
		return frappe.db.get_value("Buzz Event", self.event, "og_image")


class TestBannerPattern(UnitTestCase):
	def test_matches_the_page_script(self):
		# Values produced by bannerPattern() in event_banner.ts
		expected = {
			"MangaloreFOSS 2026": (87, -2, 58, 61, 22.9),
			"Frappe Partner Meetup: Pune": (2, 2, 84, 93, 23.5),
			"Open Source Maintainer Summit": (105, 107, 73, 101, 22.5),
		}
		for title, values in expected.items():
			self.assertEqual(tuple(banner_pattern(title).values()), values, title)


def og_files(event: str) -> list:
	return frappe.get_all(
		"File", filters={"attached_to_name": event, "attached_to_field": "og_image"}, pluck="file_url"
	)
