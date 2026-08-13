import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.teams import get_my_teams, get_team_overview
from buzz.api.teams.exceptions import NotATeamMember
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


class TestGetTeamOverview(IntegrationTestCase):
	# Rollback is per class, not per test — every test owns its user and its team names.
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def overview_for(self, user: str, team: str):
		frappe.set_user(user)
		return get_team_overview(team)

	def test_returns_the_team_and_the_callers_role(self):
		user = create_user("overview-owner@example.com", "Owner")
		team = create_owned_team("Overview Owned", user)

		overview = self.overview_for(user, team)

		self.assertEqual(overview.name, team)
		self.assertEqual(overview.team_name, "Overview Owned")
		self.assertEqual(overview.slug, "overview-owned")
		self.assertEqual(overview.my_role, "Owner")

	def test_lists_enabled_members_only(self):
		owner = create_user("overview-host@example.com", "Host")
		viewer = create_user("overview-viewer@example.com", "Viewer")
		lapsed = create_user("overview-lapsed@example.com", "Lapsed")
		team = create_owned_team("Overview Members", owner)
		upsert_membership(team, viewer, "Viewer")
		upsert_membership(team, lapsed, "Manager")
		frappe.db.set_value("Buzz Team Membership", {"team": team, "user": lapsed}, "enabled", 0)

		members = self.overview_for(viewer, team).members

		self.assertEqual(sorted(member.user for member in members), sorted([owner, viewer]))
		self.assertEqual({member.user: member.team_role for member in members}[viewer], "Viewer")

	def test_a_viewer_reads_the_team_despite_no_read_permission(self):
		user = create_user("overview-no-perm@example.com", "Viewer")
		team = create_owned_team("Overview No Perm", create_user("overview-admin@example.com", "Admin"))
		upsert_membership(team, user, "Viewer")

		frappe.set_user(user)
		self.assertFalse(frappe.has_permission("Buzz Team", doc=team))
		self.assertEqual(get_team_overview(team).name, team)

	def test_refuses_a_team_the_user_is_not_on(self):
		user = create_user("overview-outsider@example.com", "Outsider")
		team = create_owned_team("Overview Outsider", create_user("overview-insider@example.com", "Insider"))

		frappe.set_user(user)
		with self.assertRaises(NotATeamMember):
			get_team_overview(team)
