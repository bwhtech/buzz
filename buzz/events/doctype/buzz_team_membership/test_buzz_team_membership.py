# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.test_buzz_team import create_user

OWNER = "membership-owner@example.com"
MEMBER = "membership-member@example.com"


class TestBuzzTeamMembership(IntegrationTestCase):
	# Rollback is per class, not per test — every test needs its own team name and user.
	def setUp(self):
		frappe.set_user("Administrator")
		create_user(OWNER, "Owner")
		create_user(MEMBER, "Member")

	def create_team(self, team_name: str) -> "frappe.Document":
		team = frappe.get_doc({"doctype": "Buzz Team", "team_name": team_name})
		team.flags.owner_user = OWNER
		return team.insert()

	def add_member(self, team: str, user: str, team_role: str = "Manager") -> "frappe.Document":
		return frappe.get_doc(
			{
				"doctype": "Buzz Team Membership",
				"team": team,
				"user": user,
				"team_role": team_role,
			}
		).insert()

	def roles_of(self, user: str) -> set[str]:
		# Read Has Role directly: frappe.get_roles is cached per request.
		return set(frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role"))

	def test_manager_membership_grants_event_manager(self):
		user = create_user("role-manager@example.com", "Manager")
		team = self.create_team("Manager Role Team")

		self.add_member(team.name, user, "Manager")

		self.assertIn("Event Manager", self.roles_of(user))

	def test_frontdesk_membership_grants_frontdesk_manager_only(self):
		user = create_user("role-frontdesk@example.com", "Frontdesk")
		team = self.create_team("Frontdesk Role Team")

		self.add_member(team.name, user, "Frontdesk")

		roles = self.roles_of(user)
		self.assertIn("Frontdesk Manager", roles)
		self.assertNotIn("Event Manager", roles)

	def test_disabling_a_membership_revokes_its_role(self):
		user = create_user("role-revoked@example.com", "Revoked")
		team = self.create_team("Revoke Role Team")
		membership = self.add_member(team.name, user, "Frontdesk")

		membership.enabled = 0
		membership.save()

		self.assertNotIn("Frontdesk Manager", self.roles_of(user))

	def test_role_survives_while_another_team_still_earns_it(self):
		user = create_user("role-two-teams@example.com", "Two Teams")
		first = self.create_team("First Role Team")
		second = self.create_team("Second Role Team")
		membership = self.add_member(first.name, user, "Manager")
		self.add_member(second.name, user, "Manager")

		membership.enabled = 0
		membership.save()

		self.assertIn("Event Manager", self.roles_of(user))

	def test_deleting_a_membership_revokes_its_role(self):
		user = create_user("role-deleted@example.com", "Deleted")
		team = self.create_team("Delete Role Team")
		membership = self.add_member(team.name, user, "Manager")

		membership.delete()

		self.assertNotIn("Event Manager", self.roles_of(user))

	def owner_membership(self, team: str) -> "frappe.Document":
		return frappe.get_last_doc("Buzz Team Membership", filters={"team": team, "team_role": "Owner"})

	def test_owner_membership_cannot_be_disabled(self):
		team = self.create_team("Owner Disable Team")
		membership = self.owner_membership(team.name)

		membership.enabled = 0

		self.assertRaises(frappe.ValidationError, membership.save)

	def test_owner_membership_cannot_be_created_disabled(self):
		user = create_user("owner-born-disabled@example.com", "Disabled Owner")
		team = self.create_team("Disabled Owner Team")

		membership = frappe.get_doc(
			{
				"doctype": "Buzz Team Membership",
				"team": team.name,
				"user": user,
				"team_role": "Owner",
				"enabled": 0,
			}
		)

		self.assertRaises(frappe.ValidationError, membership.insert)

	def test_owner_membership_cannot_be_demoted(self):
		team = self.create_team("Owner Demote Team")
		membership = self.owner_membership(team.name)

		membership.team_role = "Viewer"

		self.assertRaises(frappe.ValidationError, membership.save)

	def test_non_owner_membership_can_be_disabled(self):
		team = self.create_team("Member Disable Team")
		membership = self.add_member(team.name, MEMBER)

		membership.enabled = 0
		membership.save()

		self.assertEqual(frappe.db.get_value("Buzz Team Membership", membership.name, "enabled"), 0)

	def test_duplicate_membership_is_rejected(self):
		team = self.create_team("Duplicate Membership Team")
		self.add_member(team.name, MEMBER)

		duplicate = frappe.get_doc(
			{
				"doctype": "Buzz Team Membership",
				"team": team.name,
				"user": MEMBER,
				"team_role": "Viewer",
			}
		)

		self.assertRaises(frappe.ValidationError, duplicate.insert)
