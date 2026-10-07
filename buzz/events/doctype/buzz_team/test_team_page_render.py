from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.website.serve import get_response, get_response_content

from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory


class TestTeamPageRender(IntegrationTestCase):
	def setUp(self):
		# CI never runs bench build, so there is no assets.json for bundled_asset to read
		assets_patch = patch("frappe.utils.get_assets_json", return_value={})
		assets_patch.start()
		self.addCleanup(assets_patch.stop)
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")

	def published_team(self, team_name: str, **overrides):
		frappe.set_user("Administrator")
		team = BuzzTeamFactory.create_owned_by(team_name=team_name, is_published=1, **overrides)
		frappe.set_user("Guest")
		return team

	def test_a_guest_sees_the_published_page(self):
		team = self.published_team("Rendered Builders", short_description="We build in public.")
		frappe.set_user("Administrator")
		BuzzEventFactory.create(title="Rendered Meetup", team=team.name)
		frappe.set_user("Guest")

		html = get_response_content(f"/{team.route}")

		self.assertIn("Rendered Builders", html)
		self.assertIn("We build in public.", html)
		self.assertIn("Rendered Meetup", html)
		self.assertIn("es-tab-buttons", html)

	def test_a_signed_in_visitor_sees_the_page(self):
		team = self.published_team("Signed In Builders")
		frappe.set_user("Administrator")

		response = get_response(f"/{team.route}")

		self.assertEqual(response.status_code, 200)

	def test_a_team_with_no_events_still_renders(self):
		team = self.published_team("Empty Builders")

		html = get_response_content(f"/{team.route}")

		self.assertIn("No upcoming events.", html)
		self.assertIn("No past events.", html)

	def test_unpublishing_takes_the_page_down_at_once(self):
		team = self.published_team("Fleeting Builders")
		self.assertEqual(get_response(f"/{team.route}").status_code, 200)

		frappe.set_user("Administrator")
		team.reload()
		team.is_published = 0
		team.save()
		frappe.set_user("Guest")

		self.assertEqual(get_response(f"/{team.route}").status_code, 404)

	def test_the_context_opts_out_of_the_page_cache(self):
		# Developer mode never caches pages, so the flag itself is what can be checked.
		team = self.published_team("Fresh Builders")
		context = frappe._dict()

		frappe.get_doc("Buzz Team", team.name).get_context(context)

		self.assertEqual(context.no_cache, 1)
