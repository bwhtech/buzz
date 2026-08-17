import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.teams import get_my_teams
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.events.doctype.buzz_team_membership.buzz_team_membership import upsert_membership


class TestGetMyTeams(IntegrationTestCase):
	# Rollback is per class, not per test — every test owns its user and its team names.
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def team_names_for(self, user: str) -> list[str]:
		frappe.set_user(user)
		return [team.name for team in get_my_teams()]

	def test_returns_owned_team_with_role_and_title(self):
		user = create_user("switcher-owner@example.com", "Owner")
		team = create_owned_team("Switcher Owned", user)

		frappe.set_user(user)
		options = get_my_teams()

		self.assertEqual(len(options), 1)
		self.assertEqual(options[0].name, team)
		self.assertEqual(options[0].team_name, "Switcher Owned")
		self.assertEqual(options[0].team_role, "Owner")

	def test_returns_every_team_the_user_belongs_to(self):
		user = create_user("switcher-multi@example.com", "Multi")
		owned = create_owned_team("Switcher Multi Owned", user)
		joined = create_owned_team("Switcher Multi Joined", create_user("switcher-host@example.com", "Host"))
		upsert_membership(joined, user, "Viewer")

		self.assertEqual(sorted(self.team_names_for(user)), sorted([owned, joined]))

	def test_a_viewer_sees_the_team_despite_no_read_permission(self):
		user = create_user("switcher-viewer@example.com", "Viewer")
		team = create_owned_team("Switcher Viewer", create_user("switcher-admin@example.com", "Admin"))
		upsert_membership(team, user, "Viewer")

		frappe.set_user(user)
		self.assertFalse(frappe.has_permission("Buzz Team", doc=team))
		self.assertEqual([option.name for option in get_my_teams()], [team])

	def test_skips_disabled_memberships(self):
		user = create_user("switcher-disabled@example.com", "Lapsed")
		team = create_owned_team("Switcher Disabled", create_user("switcher-owner2@example.com", "Owner"))
		upsert_membership(team, user, "Manager")
		frappe.db.set_value("Buzz Team Membership", {"team": team, "user": user}, "enabled", 0)

		self.assertEqual(self.team_names_for(user), [])

	def test_returns_nothing_for_a_user_on_no_team(self):
		user = create_user("switcher-teamless@example.com", "Teamless")

		self.assertEqual(self.team_names_for(user), [])
