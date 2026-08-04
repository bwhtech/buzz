# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.core.api.user_invitation import invite_by_email
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.test_buzz_team import create_user

OWNER = "membership-owner@example.com"
MEMBER = "membership-member@example.com"
INVITER = "invite-owner@example.com"


def create_team(team_name: str, owner_user: str = OWNER) -> "frappe.Document":
	team = frappe.get_doc({"doctype": "Buzz Team", "team_name": team_name})
	team.flags.owner_user = owner_user
	return team.insert()


def add_member(team: str, user: str, team_role: str = "Manager") -> "frappe.Document":
	return frappe.get_doc(
		{
			"doctype": "Buzz Team Membership",
			"team": team,
			"user": user,
			"team_role": team_role,
		}
	).insert()


class TestBuzzTeamMembership(IntegrationTestCase):
	# Rollback is per class, not per test — every test needs its own team name and user.
	def setUp(self):
		frappe.set_user("Administrator")
		create_user(OWNER, "Owner")
		create_user(MEMBER, "Member")

	def test_manager_membership_grants_event_manager(self):
		user = create_user("role-manager@example.com", "Manager")
		team = create_team("Manager Role Team")

		add_member(team.name, user, "Manager")

		self.assertIn("Event Manager", frappe.get_roles(user))

	def test_frontdesk_membership_grants_frontdesk_manager_only(self):
		user = create_user("role-frontdesk@example.com", "Frontdesk")
		team = create_team("Frontdesk Role Team")

		add_member(team.name, user, "Frontdesk")

		roles = frappe.get_roles(user)
		self.assertIn("Frontdesk Manager", roles)
		self.assertNotIn("Event Manager", roles)

	def test_disabling_a_membership_revokes_its_role(self):
		user = create_user("role-revoked@example.com", "Revoked")
		team = create_team("Revoke Role Team")
		membership = add_member(team.name, user, "Frontdesk")

		membership.enabled = 0
		membership.save()

		self.assertNotIn("Frontdesk Manager", frappe.get_roles(user))

	def test_role_survives_while_another_team_still_earns_it(self):
		user = create_user("role-two-teams@example.com", "Two Teams")
		first = create_team("First Role Team")
		second = create_team("Second Role Team")
		membership = add_member(first.name, user, "Manager")
		add_member(second.name, user, "Manager")

		membership.enabled = 0
		membership.save()

		self.assertIn("Event Manager", frappe.get_roles(user))

	def test_deleting_a_membership_revokes_its_role(self):
		user = create_user("role-deleted@example.com", "Deleted")
		team = create_team("Delete Role Team")
		membership = add_member(team.name, user, "Manager")

		membership.delete()

		self.assertNotIn("Event Manager", frappe.get_roles(user))

	def owner_membership(self, team: str) -> "frappe.Document":
		return frappe.get_last_doc("Buzz Team Membership", filters={"team": team, "team_role": "Owner"})

	def test_owner_membership_cannot_be_disabled(self):
		team = create_team("Owner Disable Team")
		membership = self.owner_membership(team.name)

		membership.enabled = 0

		self.assertRaises(frappe.ValidationError, membership.save)

	def test_owner_membership_cannot_be_created_disabled(self):
		user = create_user("owner-born-disabled@example.com", "Disabled Owner")
		team = create_team("Disabled Owner Team")

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
		team = create_team("Owner Demote Team")
		membership = self.owner_membership(team.name)

		membership.team_role = "Viewer"

		self.assertRaises(frappe.ValidationError, membership.save)

	def test_non_owner_membership_can_be_disabled(self):
		team = create_team("Member Disable Team")
		membership = add_member(team.name, MEMBER)

		membership.enabled = 0
		membership.save()

		self.assertEqual(frappe.db.get_value("Buzz Team Membership", membership.name, "enabled"), 0)

	def test_duplicate_membership_is_rejected(self):
		team = create_team("Duplicate Membership Team")
		add_member(team.name, MEMBER)

		duplicate = frappe.get_doc(
			{
				"doctype": "Buzz Team Membership",
				"team": team.name,
				"user": MEMBER,
				"team_role": "Viewer",
			}
		)

		self.assertRaises(frappe.ValidationError, duplicate.insert)


class TestInvitationAccept(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		# Every invitation mails itself out on insert, which needs an outgoing email account.
		self.enterContext(patch("frappe.sendmail"))
		create_user(INVITER, "Inviter")
		self.team = create_team(f"Invite Team {frappe.generate_hash(length=6)}", INVITER)

	def invite(self, email: str, team_role: str = "Manager", inviter: str = INVITER, team: str | None = None):
		try:
			frappe.set_user(inviter)
			invite_by_email(
				emails=email,
				roles=["Buzz User"],
				redirect_to_path="/dashboard",
				app_name="buzz",
				buzz_team=team or self.team.name,
				buzz_team_role=team_role,
			)
		finally:
			frappe.set_user("Administrator")
		return frappe.get_last_doc("User Invitation", filters={"email": email})

	def memberships_of(self, user: str) -> list[dict]:
		return frappe.get_all(
			"Buzz Team Membership",
			filters={"team": self.team.name, "user": user},
			fields=["name", "team_role", "enabled"],
		)

	def test_invitation_persists_the_team_and_role(self):
		invitation = self.invite("invitee-persisted@example.com")

		stored = frappe.db.get_value(
			"User Invitation", invitation.name, ["buzz_team", "buzz_team_role"], as_dict=True
		)

		self.assertEqual(stored.buzz_team, self.team.name)
		self.assertEqual(stored.buzz_team_role, "Manager")

	def test_accept_creates_an_enabled_membership_with_the_invited_role(self):
		email = "invitee-new@example.com"
		invitation = self.invite(email, "Frontdesk")

		invitation.accept(ignore_permissions=True)

		memberships = self.memberships_of(email)
		self.assertEqual(len(memberships), 1)
		self.assertEqual(memberships[0].team_role, "Frontdesk")
		self.assertTrue(memberships[0].enabled)
		self.assertIn("Frontdesk Manager", frappe.get_roles(email))

	def test_accept_works_for_a_logged_out_invitee(self):
		# The accept endpoint is allow_guest: a brand-new invitee is Guest while the hook runs.
		email = "invitee-guest@example.com"
		invitation = self.invite(email)

		try:
			frappe.set_user("Guest")
			invitation.accept(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(len(self.memberships_of(email)), 1)
		self.assertIn("Event Manager", frappe.get_roles(email))

	def test_accept_re_enables_a_disabled_membership(self):
		email = create_user("invitee-disabled@example.com", "Disabled Invitee")
		membership = add_member(self.team.name, email, "Viewer")
		membership.enabled = 0
		membership.save()
		invitation = self.invite(email, "Manager")

		invitation.accept(ignore_permissions=True)

		memberships = self.memberships_of(email)
		self.assertEqual(len(memberships), 1)
		self.assertTrue(memberships[0].enabled)
		self.assertEqual(memberships[0].team_role, "Manager")

	def test_accept_for_an_enabled_member_changes_nothing(self):
		email = create_user("invitee-member@example.com", "Existing Member")
		add_member(self.team.name, email, "Viewer")
		invitation = self.invite(email, "Manager")

		invitation.accept(ignore_permissions=True)

		memberships = self.memberships_of(email)
		self.assertEqual(len(memberships), 1)
		self.assertEqual(memberships[0].team_role, "Viewer")

	def test_accept_is_refused_when_the_inviter_is_not_owner_or_admin(self):
		manager = create_user("invite-manager@example.com", "Inviting Manager")
		add_member(self.team.name, manager, "Manager")
		email = "invitee-of-manager@example.com"
		invitation = self.invite(email, inviter=manager)

		self.assertRaises(frappe.ValidationError, invitation.accept, True)

		self.assertEqual(self.memberships_of(email), [])

	def test_accept_is_refused_when_the_inviter_left_the_team(self):
		outsider = create_user("invite-outsider@example.com", "Outsider")
		frappe.get_doc("User", outsider).add_roles("Event Manager")
		email = "invitee-of-outsider@example.com"
		invitation = self.invite(email, inviter=outsider)

		self.assertRaises(frappe.ValidationError, invitation.accept, True)

		self.assertEqual(self.memberships_of(email), [])

	def test_accept_is_refused_when_the_invitation_grants_ownership(self):
		email = "invitee-owner@example.com"
		invitation = self.invite(email, "Owner")

		self.assertRaises(frappe.ValidationError, invitation.accept, True)

		self.assertEqual(self.memberships_of(email), [])

	def test_accept_is_refused_when_the_invitation_names_no_team(self):
		invitation = frappe.get_doc(
			{
				"doctype": "User Invitation",
				"email": "invitee-teamless@example.com",
				"roles": [{"role": "Buzz User"}],
				"app_name": "buzz",
				"redirect_to_path": "/dashboard",
			}
		).insert(ignore_permissions=True)

		self.assertRaises(frappe.ValidationError, invitation.accept, True)

	def test_invitation_to_an_unknown_team_is_rejected_at_invite_time(self):
		self.assertRaises(
			frappe.LinkValidationError, self.invite, "invitee-no-team@example.com", team="No Such Team"
		)
