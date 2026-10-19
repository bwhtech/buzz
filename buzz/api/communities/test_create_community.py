import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.communities import check_community_slug, create_community
from buzz.api.communities.exceptions import CommunitiesDisabled, LoginRequired
from buzz.api.teams.exceptions import TeamSlugTaken
from buzz.tests.factories import BuzzTeamFactory, UserFactory


class TestCreateCommunity(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.founder = UserFactory.create_once("community-founder@example.com").name
		cls.taken = BuzzTeamFactory.create_owned_by(slug="taken-community").slug

	def setUp(self):
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")
		self.enterContext(self.change_settings("Buzz Settings", enable_communities=1))

	def test_a_guest_checks_a_slug(self):
		with self.set_user("Guest"):
			self.assertTrue(check_community_slug("Night Owls").available)
			self.assertFalse(check_community_slug(self.taken).available)

	def test_a_user_creates_a_live_community(self):
		with self.set_user(self.founder):
			created = create_community("Night Owls", "Night Owls")

		team = frappe.get_doc("Buzz Team", created.team)
		self.assertEqual(created.route, "/community/night-owls")
		self.assertTrue(team.is_published)
		self.assertTrue(team.accept_community_submissions)
		role = frappe.db.get_value(
			"Buzz Team Membership", {"team": team.name, "user": self.founder}, "team_role"
		)
		self.assertEqual(role, "Owner")

	def test_a_taken_slug_is_refused(self):
		with self.set_user(self.founder), self.assertRaises(TeamSlugTaken):
			create_community("Copycats", self.taken)

	def test_a_guest_cannot_create(self):
		with self.set_user("Guest"), self.assertRaises(LoginRequired):
			create_community("Night Owls", "night-owls")

	def test_nothing_works_while_communities_are_off(self):
		with self.change_settings("Buzz Settings", enable_communities=0), self.set_user(self.founder):
			self.assertRaises(CommunitiesDisabled, check_community_slug, "night-owls")
			self.assertRaises(CommunitiesDisabled, create_community, "Night Owls", "night-owls")
