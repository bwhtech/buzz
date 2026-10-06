import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.teams import change_roles, remove_members
from buzz.api.teams.exceptions import (
	CannotGrantOwnership,
	CannotManageMembers,
	NotATeamMember,
	UnknownTeamRole,
)
from buzz.tests.factories import BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory


class MemberRoleTestCase(IntegrationTestCase):
	# Roles span teams and rollback is per class, so every test owns its users.
	def create_user(self, email: str) -> str:
		return UserFactory.create_once(email).name

	def create_team(self, owner: str, *members: tuple[str, str]) -> str:
		team = BuzzTeamFactory.create_owned_by(owner).name
		for user, team_role in members:
			BuzzTeamMembershipFactory.create(team=team, user=user, team_role=team_role)
		return team


class TestRemoveMember(MemberRoleTestCase):
	def test_an_admin_disables_the_membership_instead_of_deleting_it(self):
		admin = self.create_user("remove-admin@example.com")
		member = self.create_user("remove-member@example.com")
		team = self.create_team(
			self.create_user("remove-owner@example.com"), (admin, "Admin"), (member, "Manager")
		)

		with self.set_user(admin):
			remove_members(team, [member])

		self.assertEqual(self.membership_enabled(team, member), 0)

	def test_a_manager_cannot_remove_anyone(self):
		manager = self.create_user("remove-manager@example.com")
		member = self.create_user("remove-managers-target@example.com")
		team = self.create_team(
			self.create_user("remove-owner2@example.com"), (manager, "Manager"), (member, "Viewer")
		)

		with self.set_user(manager), self.assertRaises(CannotManageMembers):
			remove_members(team, [member])

	def test_an_outsider_cannot_remove_anyone(self):
		owner = self.create_user("remove-owner3@example.com")
		team = self.create_team(owner)

		with (
			self.set_user(self.create_user("remove-outsider@example.com")),
			self.assertRaises(CannotManageMembers),
		):
			remove_members(team, [owner])

	def test_the_owner_cannot_be_removed(self):
		owner = self.create_user("remove-locked-owner@example.com")
		admin = self.create_user("remove-owners-admin@example.com")
		team = self.create_team(owner, (admin, "Admin"))

		with self.set_user(admin), self.assertRaises(frappe.ValidationError):
			remove_members(team, [owner])

	def test_refuses_a_user_who_is_not_on_the_team(self):
		owner = self.create_user("remove-stranger-owner@example.com")
		stranger = self.create_user("remove-stranger@example.com")
		team = self.create_team(owner)

		with self.set_user(owner), self.assertRaises(NotATeamMember):
			remove_members(team, [stranger])

	def test_removing_the_same_member_twice_is_refused(self):
		owner = self.create_user("remove-twice-owner@example.com")
		member = self.create_user("remove-twice-member@example.com")
		team = self.create_team(owner, (member, "Manager"))

		with self.set_user(owner):
			remove_members(team, [member])

			with self.assertRaises(NotATeamMember):
				remove_members(team, [member])

	def test_the_desk_role_survives_while_another_team_still_earns_it(self):
		owner = self.create_user("remove-roles-owner@example.com")
		member = self.create_user("remove-roles-member@example.com")
		first = self.create_team(owner, (member, "Manager"))
		second = self.create_team(owner, (member, "Manager"))

		with self.set_user(owner):
			remove_members(first, [member])
			self.assertIn("Event Manager", frappe.get_roles(member))

			remove_members(second, [member])
			self.assertNotIn("Event Manager", frappe.get_roles(member))

	def test_an_admin_removes_several_members_at_once(self):
		owner = self.create_user("remove-batch-owner@example.com")
		first = self.create_user("remove-batch-first@example.com")
		second = self.create_user("remove-batch-second@example.com")
		team = self.create_team(owner, (first, "Manager"), (second, "Viewer"))

		with self.set_user(owner):
			remove_members(team, [first, second])

		self.assertEqual(self.membership_enabled(team, first), 0)
		self.assertEqual(self.membership_enabled(team, second), 0)

	def membership_enabled(self, team: str, user: str) -> int:
		return frappe.db.get_value("Buzz Team Membership", {"team": team, "user": user}, "enabled")


class TestChangeRole(MemberRoleTestCase):
	def test_an_admin_promotes_a_manager(self):
		admin = self.create_user("role-admin@example.com")
		member = self.create_user("role-member@example.com")
		team = self.create_team(
			self.create_user("role-owner@example.com"), (admin, "Admin"), (member, "Manager")
		)

		with self.set_user(admin):
			change_roles(team, [member], "Admin")

		self.assertEqual(self.role(team, member), "Admin")

	def test_a_demoted_member_loses_the_desk_role_the_old_one_earned(self):
		owner = self.create_user("role-demote-owner@example.com")
		member = self.create_user("role-demote-member@example.com")
		team = self.create_team(owner, (member, "Manager"))
		self.assertIn("Event Manager", frappe.get_roles(member))

		with self.set_user(owner):
			change_roles(team, [member], "Viewer")

		self.assertNotIn("Event Manager", frappe.get_roles(member))

	def test_an_admin_may_demote_another_admin(self):
		admin = self.create_user("role-peer-admin@example.com")
		peer = self.create_user("role-peer@example.com")
		team = self.create_team(
			self.create_user("role-peer-owner@example.com"), (admin, "Admin"), (peer, "Admin")
		)

		with self.set_user(admin):
			change_roles(team, [peer], "Viewer")

		self.assertEqual(self.role(team, peer), "Viewer")

	def test_a_manager_cannot_change_anyone(self):
		manager = self.create_user("role-manager@example.com")
		member = self.create_user("role-managers-target@example.com")
		team = self.create_team(
			self.create_user("role-manager-owner@example.com"), (manager, "Manager"), (member, "Viewer")
		)

		with self.set_user(manager), self.assertRaises(CannotManageMembers):
			change_roles(team, [member], "Manager")

	def test_an_outsider_cannot_change_anyone(self):
		member = self.create_user("role-outsiders-target@example.com")
		team = self.create_team(self.create_user("role-outsider-owner@example.com"), (member, "Viewer"))

		with (
			self.set_user(self.create_user("role-outsider@example.com")),
			self.assertRaises(CannotManageMembers),
		):
			change_roles(team, [member], "Manager")

	def test_the_owner_cannot_be_given_another_role(self):
		owner = self.create_user("role-locked-owner@example.com")
		admin = self.create_user("role-owners-admin@example.com")
		team = self.create_team(owner, (admin, "Admin"))

		with self.set_user(admin), self.assertRaises(frappe.ValidationError):
			change_roles(team, [owner], "Viewer")

	def test_ownership_cannot_be_granted(self):
		owner = self.create_user("role-grant-owner@example.com")
		member = self.create_user("role-grant-member@example.com")
		team = self.create_team(owner, (member, "Manager"))

		with self.set_user(owner), self.assertRaises(CannotGrantOwnership):
			change_roles(team, [member], "Owner")

	def test_an_unknown_role_is_refused(self):
		owner = self.create_user("role-unknown-owner@example.com")
		member = self.create_user("role-unknown-member@example.com")
		team = self.create_team(owner, (member, "Manager"))

		with self.set_user(owner), self.assertRaises(UnknownTeamRole):
			change_roles(team, [member], "Overlord")

	def test_refuses_a_user_who_is_not_on_the_team(self):
		owner = self.create_user("role-stranger-owner@example.com")
		stranger = self.create_user("role-stranger@example.com")
		team = self.create_team(owner)

		with self.set_user(owner), self.assertRaises(NotATeamMember):
			change_roles(team, [stranger], "Manager")

	def test_refuses_a_member_whose_membership_is_disabled(self):
		owner = self.create_user("role-disabled-owner@example.com")
		member = self.create_user("role-disabled-member@example.com")
		team = self.create_team(owner, (member, "Manager"))

		with self.set_user(owner):
			remove_members(team, [member])

			with self.assertRaises(NotATeamMember):
				change_roles(team, [member], "Viewer")

	def test_an_admin_re_roles_several_members_at_once(self):
		owner = self.create_user("role-batch-owner@example.com")
		first = self.create_user("role-batch-first@example.com")
		second = self.create_user("role-batch-second@example.com")
		team = self.create_team(owner, (first, "Manager"), (second, "Frontdesk"))

		with self.set_user(owner):
			change_roles(team, [first, second], "Viewer")

		self.assertEqual(self.role(team, first), "Viewer")
		self.assertEqual(self.role(team, second), "Viewer")

	def role(self, team: str, user: str) -> str:
		return frappe.db.get_value("Buzz Team Membership", {"team": team, "user": user}, "team_role")
