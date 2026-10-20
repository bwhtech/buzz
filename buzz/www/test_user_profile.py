from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response, get_response_content

from buzz.events.doctype.buzz_team.buzz_team import create_personal_team_for
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, UserFactory


class TestUserProfile(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.user = UserFactory.create_once("profile-host@example.com")
		cls.user.update({"first_name": "Noor", "last_name": "Host", "bio": "Hosts reading circles."})
		cls.user.save(ignore_permissions=True)
		cls.team = create_personal_team_for(cls.user.name).name
		cls.event = BuzzEventFactory.create(team=cls.team, title="Noor's Reading Circle")

	def setUp(self):
		# CI never runs bench build, so there is no assets.json for bundled_asset to read
		assets_patch = patch("frappe.utils.get_assets_json", return_value={})
		assets_patch.start()
		self.addCleanup(assets_patch.stop)
		self.enterContext(self.change_settings("Buzz Settings", enable_personal_teams=1))

	def test_profile_shows_the_host_and_their_events(self):
		html = self.visit(self.profile_url(), get_response_content)

		self.assertIn("Noor Host", html)
		self.assertIn("Hosts reading circles.", html)
		self.assertIn("Noor&#39;s Reading Circle", html)

	def test_bio_is_shown_as_text(self):
		frappe.db.set_value("User", self.user.name, "bio", "<script>alert(1)</script>")
		self.addCleanup(frappe.db.set_value, "User", self.user.name, "bio", "Hosts reading circles.")

		html = self.visit(self.profile_url(), get_response_content)

		self.assertNotIn("<script>alert(1)</script>", html)

	def test_profile_follows_a_renamed_username(self):
		old_url = self.profile_url()
		frappe.db.set_value("User", self.user.name, "username", f"noor-{frappe.generate_hash(length=4)}")

		self.assertEqual(self.visit(self.profile_url()).status_code, 200)
		self.assertEqual(self.visit(old_url).status_code, 404)

	def test_profile_is_hidden_until_an_event_is_published(self):
		user = UserFactory.create()
		team = create_personal_team_for(user.name).name
		BuzzEventFactory.create("unpublished", team=team)

		self.assertEqual(self.visit(self.profile_url(user.name)).status_code, 404)

	def test_events_of_a_regular_team_do_not_make_a_profile(self):
		username = f"regular-{frappe.generate_hash(length=6)}"
		user = UserFactory.create(username=username)
		BuzzEventFactory.create(team=BuzzTeamFactory.create_owned_by(user.name).name)

		self.assertEqual(self.visit(f"/u/{username}").status_code, 404)

	def test_unknown_username_is_not_found(self):
		self.assertEqual(self.visit("/u/nobody-by-this-name").status_code, 404)

	def test_profile_is_hidden_while_personal_teams_are_off(self):
		with self.change_settings("Buzz Settings", enable_personal_teams=0):
			self.assertEqual(self.visit(self.profile_url()).status_code, 404)

	def visit(self, url: str, render=get_response):
		with self.set_user("Guest"):
			# Route rules resolve only against a request.
			set_request(method="GET", path=url)
			return render(url)

	def profile_url(self, user: str | None = None) -> str:
		return f"/u/{frappe.db.get_value('User', user or self.user.name, 'username')}"
