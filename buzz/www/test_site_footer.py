from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.website.serve import get_response_content

from buzz.www.site_footer import SiteFooter
from buzz.www.site_header import BUZZ_FOOTER


class TestSiteFooter(IntegrationTestCase):
	def setUp(self):
		# CI never runs bench build, so there is no assets.json for bundled_asset to read
		assets_patch = patch("frappe.utils.get_assets_json", return_value={})
		assets_patch.start()
		self.addCleanup(assets_patch.stop)

	def test_footer_items_split_into_groups_and_links(self):
		self.set_footer_items(
			[
				{"label": "Company"},
				{"label": "About", "url": "/about", "parent_label": "Company"},
				{"label": "Privacy", "url": "/privacy"},
			]
		)

		context = SiteFooter().as_context()

		self.assertEqual([group["label"] for group in context["groups"]], ["Company"])
		self.assertEqual([link["url"] for link in context["groups"][0]["child_items"]], ["/about"])
		self.assertEqual([link["url"] for link in context["links"]], ["/privacy"])

	def test_buzz_pages_render_the_buzz_footer(self):
		html = self.render_page(BUZZ_FOOTER)

		self.assertIn("buzz-footer", html)
		self.assertNotIn("website.bundle", html)

	def test_buzz_pages_render_the_footer_the_site_chose(self):
		html = self.render_page("Standard Footer")

		self.assertNotIn("buzz-footer", html)
		self.assertIn("web-footer", html)
		self.assertIn("website.bundle", html)

	def render_page(self, footer_template: str) -> str:
		with (
			self.change_settings("Buzz Settings", enable_communities=1),
			self.change_settings("Website Settings", footer_template=footer_template),
		):
			return get_response_content("/community")

	def set_footer_items(self, items: list[dict]):
		settings = frappe.get_doc("Website Settings")
		previous_items = [item.as_dict() for item in settings.footer_items]
		settings.set("footer_items", items)
		settings.save()
		self.addCleanup(self.restore_footer_items, previous_items)

	def restore_footer_items(self, items: list[dict]):
		settings = frappe.get_doc("Website Settings")
		settings.set("footer_items", items)
		settings.save()
