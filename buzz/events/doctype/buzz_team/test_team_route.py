import frappe
from frappe.tests import IntegrationTestCase
from frappe.website.page_renderers.document_page import DocumentPage
from frappe.website.page_renderers.not_found_page import NotFoundPage
from frappe.website.path_resolver import PathResolver

from buzz.tests.factories import BuzzTeamFactory


class TestTeamRoute(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def publish(self, team):
		team.is_published = 1
		team.save()
		return team

	def test_publishing_sets_the_community_route(self):
		team = self.publish(BuzzTeamFactory.create_owned_by(team_name="Route Builders"))

		self.assertEqual(team.route, f"community/{team.slug}")

	def test_an_unpublished_team_has_no_route(self):
		team = BuzzTeamFactory.create_owned_by(team_name="Quiet Builders")

		self.assertFalse(team.route)

	def test_a_published_team_resolves_to_its_document(self):
		team = self.publish(BuzzTeamFactory.create_owned_by(team_name="Resolved Builders"))

		_, renderer = PathResolver(team.route).resolve()

		self.assertIsInstance(renderer, DocumentPage)
		self.assertEqual((renderer.doctype, renderer.docname), ("Buzz Team", team.name))

	def test_an_unpublished_team_does_not_resolve(self):
		team = self.publish(BuzzTeamFactory.create_owned_by(team_name="Hidden Builders"))
		team.is_published = 0
		team.save()

		_, renderer = PathResolver(team.route).resolve()

		self.assertIsInstance(renderer, NotFoundPage)

	def test_a_hand_set_top_level_route_resolves(self):
		team = self.publish(BuzzTeamFactory.create_owned_by(team_name="Featured Builders"))
		route = f"featured-builders-{frappe.generate_hash(length=6)}"
		team.route = route
		team.save()

		_, renderer = PathResolver(route).resolve()

		self.assertEqual(renderer.docname, team.name)

	def test_a_slug_edit_keeps_the_route(self):
		team = self.publish(BuzzTeamFactory.create_owned_by(team_name="Stable Builders"))
		route = team.route
		team.slug = f"renamed-{frappe.generate_hash(length=6)}"
		team.save()

		self.assertEqual(team.route, route)
