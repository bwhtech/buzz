import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.teams import get_my_teams, get_team_overview, update_public_page, update_team
from buzz.api.teams.exceptions import CannotEditTeam, NotATeamMember
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import feature_flags
from buzz.tests.factories import BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory


class TeamTestCase(IntegrationTestCase):
	def create_user(self, email: str) -> str:
		return UserFactory.create_once(email).name

	def create_team(self, owner: str, **overrides) -> str:
		return BuzzTeamFactory.create_owned_by(owner, **overrides).name

	def add_member(self, team: str, user: str, team_role: str, **overrides):
		BuzzTeamMembershipFactory.create(team=team, user=user, team_role=team_role, **overrides)


class TestGetMyTeams(TeamTestCase):
	def test_returns_owned_team_with_role_and_title(self):
		user = self.create_user("switcher-owner@example.com")
		team = self.create_team(user, team_name="Switcher Owned")

		with self.set_user(user):
			options = get_my_teams()

		self.assertEqual(len(options), 1)
		self.assertEqual(options[0].name, team)
		self.assertEqual(options[0].team_name, "Switcher Owned")
		self.assertEqual(options[0].team_role, "Owner")

	def test_returns_every_team_the_user_belongs_to(self):
		user = self.create_user("switcher-multi@example.com")
		owned = self.create_team(user)
		joined = self.create_team(self.create_user("switcher-host@example.com"))
		self.add_member(joined, user, "Viewer")

		self.assertEqual(sorted(self.team_names_for(user)), sorted([owned, joined]))

	def test_a_viewer_sees_the_team_despite_no_read_permission(self):
		user = self.create_user("switcher-viewer@example.com")
		team = self.create_team(self.create_user("switcher-admin@example.com"))
		self.add_member(team, user, "Viewer")

		with self.set_user(user):
			self.assertFalse(frappe.has_permission("Buzz Team", doc=team))
			self.assertEqual([option.name for option in get_my_teams()], [team])

	def test_skips_disabled_memberships(self):
		user = self.create_user("switcher-disabled@example.com")
		team = self.create_team(self.create_user("switcher-owner2@example.com"))
		self.add_member(team, user, "Manager", enabled=0)

		self.assertEqual(self.team_names_for(user), [])

	def test_lists_each_teams_enabled_members(self):
		owner = self.create_user("switcher-members-owner@example.com")
		viewer = self.create_user("switcher-members-viewer@example.com")
		team = self.create_team(owner)
		self.add_member(team, viewer, "Viewer")

		with self.set_user(viewer):
			members = get_my_teams()[0].members

		self.assertEqual([member.user for member in members], [owner, viewer])

	def test_a_viewer_gets_the_teams_feature_flags(self):
		user = self.create_user("switcher-flags-viewer@example.com")
		team = BuzzTeamFactory.create_owned_by().name
		self.add_member(team, user, "Viewer")

		with self.set_user(user):
			self.assertEqual(get_my_teams()[0].feature_flags, feature_flags(team))

	def test_returns_nothing_for_a_user_on_no_team(self):
		self.assertEqual(self.team_names_for(self.create_user("switcher-teamless@example.com")), [])

	def team_names_for(self, user: str) -> list[str]:
		with self.set_user(user):
			return [team.name for team in get_my_teams()]


class TestGetTeamOverview(TeamTestCase):
	def test_returns_the_team_and_the_callers_role(self):
		user = self.create_user("overview-owner@example.com")
		team = self.create_team(user, team_name="Overview Owned")

		overview = self.overview_for(user, team)

		self.assertEqual(overview.name, team)
		self.assertEqual(overview.team_name, "Overview Owned")
		self.assertEqual(overview.slug, "overview-owned")
		self.assertEqual(overview.my_role, "Owner")

	def test_lists_enabled_members_only(self):
		owner = self.create_user("overview-host@example.com")
		viewer = self.create_user("overview-viewer@example.com")
		team = self.create_team(owner)
		self.add_member(team, viewer, "Viewer")
		self.add_member(team, self.create_user("overview-lapsed@example.com"), "Manager", enabled=0)

		members = self.overview_for(viewer, team).members

		self.assertEqual(sorted(member.user for member in members), sorted([owner, viewer]))
		self.assertEqual({member.user: member.team_role for member in members}[viewer], "Viewer")

	def test_lists_the_owner_first(self):
		# The owner's name sorts last alphabetically, so only the role ordering can put them first.
		owner = UserFactory.create(first_name="Zara").name
		manager = UserFactory.create(first_name="Aditi").name
		team = self.create_team(owner)
		self.add_member(team, manager, "Manager")

		members = self.overview_for(owner, team).members

		self.assertEqual([member.user for member in members], [owner, manager])

	def test_a_viewer_reads_the_team_despite_no_read_permission(self):
		user = self.create_user("overview-no-perm@example.com")
		team = self.create_team(self.create_user("overview-admin@example.com"))
		self.add_member(team, user, "Viewer")

		with self.set_user(user):
			self.assertFalse(frappe.has_permission("Buzz Team", doc=team))
			self.assertEqual(get_team_overview(team).name, team)

	def test_refuses_a_team_the_user_is_not_on(self):
		team = self.create_team(self.create_user("overview-insider@example.com"))

		with (
			self.set_user(self.create_user("overview-outsider@example.com")),
			self.assertRaises(NotATeamMember),
		):
			get_team_overview(team)

	def overview_for(self, user: str, team: str):
		with self.set_user(user):
			return get_team_overview(team)


class TestUpdateTeam(TeamTestCase):
	def test_an_admin_renames_the_team_and_sets_its_logo(self):
		admin = self.create_user("update-admin@example.com")
		team = self.create_team(self.create_user("update-owner@example.com"), team_name="Update Before")
		self.add_member(team, admin, "Admin")

		with self.set_user(admin):
			update_team(team, "  Update After  ", "/files/logo.png")

		details = frappe.db.get_value("Buzz Team", team, ["team_name", "logo"], as_dict=True)
		self.assertEqual(details.team_name, "Update After")
		self.assertEqual(details.logo, "/files/logo.png")

	def test_a_manager_cannot_edit_the_team(self):
		manager = self.create_user("update-manager@example.com")
		team = self.create_team(self.create_user("update-owner2@example.com"))
		self.add_member(team, manager, "Manager")

		with self.set_user(manager), self.assertRaises(CannotEditTeam):
			update_team(team, "Renamed", None)

	def test_a_blank_name_is_refused(self):
		owner = self.create_user("update-owner3@example.com")
		team = self.create_team(owner)

		with self.set_user(owner), self.assertRaises(frappe.ValidationError):
			update_team(team, "   ", None)


class TestUpdatePublicPage(TeamTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("public-page-owner@example.com").name
		cls.manager = UserFactory.create_once("public-page-manager@example.com").name
		cls.viewer = UserFactory.create_once("public-page-viewer@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner, team_name="Public Page Builders").name
		for user, team_role in ((cls.manager, "Manager"), (cls.viewer, "Viewer")):
			BuzzTeamMembershipFactory.create(team=cls.team, user=user, team_role=team_role)

	def overview(self):
		with self.set_user(self.owner):
			return get_team_overview(self.team)

	def publish_as(self, user: str, **overrides):
		with self.set_user(user):
			update_public_page(**({"team": self.team, "is_published": True, "links": []} | overrides))

	def test_a_manager_publishes_the_page(self):
		self.publish_as(self.manager, short_description="Builders in public.")

		overview = self.overview()

		self.assertTrue(overview.is_published)
		self.assertEqual(overview.short_description, "Builders in public.")
		self.assertTrue(
			overview.public_url.endswith(f"/community/{frappe.db.get_value('Buzz Team', self.team, 'slug')}")
		)

	def test_links_are_saved_in_order(self):
		links = [
			{"icon": "globe", "label": "Site", "url": "https://example.com"},
			{"icon": "message-circle", "label": "Forum", "url": "https://forum.example.com"},
		]
		self.publish_as(self.owner, links=links)

		overview = self.overview()

		self.assertEqual([link.label for link in overview.links], ["Site", "Forum"])

	def test_a_viewer_cannot_edit_the_page(self):
		with self.assertRaises(CannotEditTeam):
			self.publish_as(self.viewer, short_description="Hijacked")

		self.assertNotEqual(frappe.db.get_value("Buzz Team", self.team, "short_description"), "Hijacked")

	def test_a_manager_makes_the_team_a_community(self):
		self.publish_as(self.manager, is_a_community=True)

		self.assertTrue(self.overview().is_a_community)

	def test_an_unpublished_page_has_no_public_url(self):
		self.publish_as(self.owner, is_published=False)

		self.assertIsNone(self.overview().public_url)
