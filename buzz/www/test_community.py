from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.website.serve import get_response, get_response_content

from buzz.www.community import CommunityLanding


class TestCommunityLanding(IntegrationTestCase):
	def setUp(self):
		# CI never runs bench build, so there is no assets.json for bundled_asset to read
		assets_patch = patch("frappe.utils.get_assets_json", return_value={})
		assets_patch.start()
		self.addCleanup(assets_patch.stop)
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_a_guest_sees_the_landing_page(self):
		with self.change_settings("Buzz Settings", enable_communities=1):
			html = get_response_content("/community")

		self.assertIn("hero-title", html)
		self.assertIn("data-globe", html)
		self.assertIn("es-tab-buttons", html)
		self.assertIn("team-page-data", html)
		self.assertIn("site-footer", html)

	def test_the_page_is_not_found_while_communities_are_off(self):
		with self.change_settings("Buzz Settings", enable_communities=0):
			response = get_response("/community")

		self.assertEqual(response.status_code, 404)

	def test_the_preview_splits_events_around_today(self):
		context = CommunityLanding().as_context()

		self.assertEqual(len(context["page_data"]["upcoming"]), 3)
		self.assertEqual(len(context["page_data"]["past"]), 2)
		self.assertTrue(context["has_pins"])

	def test_a_topic_named_community_moves_aside(self):
		topic = frappe.new_doc("Event Topic")
		topic.name = "Community"

		self.assertEqual(topic.make_route(), "community-events")
