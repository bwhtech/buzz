# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.core.api.user_invitation import invite_by_email
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory
from buzz.tests.factories.core.user_invitation_factory import UserInvitationFactory

OWNER = "membership-owner@example.com"
MEMBER = "membership-member@example.com"
INVITER = "invite-owner@example.com"


class TestBuzzTeamMembership(IntegrationTestCase):
	# Rollback is per class, not per test — every test needs its own team and user.
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once(OWNER).name
		cls.member = UserFactory.create_once(MEMBER).name

	def test_manager_membership_grants_event_manager(self):
		user = UserFactory.create_once("role-manager@example.com").name

		self.add_member(self.create_team(), user, "Manager")

		self.assertIn("Event Manager", frappe.get_roles(user))

	def test_membership_keeps_the_user_out_of_desk(self):
		user = UserFactory.create_once("role-no-desk@example.com").name

		self.add_member(self.create_team(), user, "Manager")

		self.assertEqual(frappe.db.get_value("User", user, "user_type"), "Website User")

	def test_frontdesk_membership_grants_frontdesk_manager_only(self):
		user = UserFactory.create_once("role-frontdesk@example.com").name

		self.add_member(self.create_team(), user, "Frontdesk")

		roles = frappe.get_roles(user)
		self.assertIn("Frontdesk Manager", roles)
		self.assertNotIn("Event Manager", roles)

	def test_disabling_a_membership_revokes_its_role(self):
		user = UserFactory.create_once("role-revoked@example.com").name
		membership = self.add_member(self.create_team(), user, "Frontdesk")

		membership.enabled = 0
		membership.save()

		self.assertNotIn("Frontdesk Manager", frappe.get_roles(user))

	def test_role_survives_while_another_team_still_earns_it(self):
		user = UserFactory.create_once("role-two-teams@example.com").name
		membership = self.add_member(self.create_team(), user, "Manager")
		self.add_member(self.create_team(), user, "Manager")

		membership.enabled = 0
		membership.save()

		self.assertIn("Event Manager", frappe.get_roles(user))

	def test_deleting_a_membership_revokes_its_role(self):
		user = UserFactory.create_once("role-deleted@example.com").name
		membership = self.add_member(self.create_team(), user, "Manager")

		membership.delete()

		self.assertNotIn("Event Manager", frappe.get_roles(user))

	def test_owner_membership_cannot_be_disabled(self):
		membership = self.owner_membership(self.create_team())

		membership.enabled = 0

		self.assertRaises(frappe.ValidationError, membership.save)

	def test_owner_membership_cannot_be_created_disabled(self):
		user = UserFactory.create_once("owner-born-disabled@example.com").name

		membership = BuzzTeamMembershipFactory.build(
			team=self.create_team(), user=user, team_role="Owner", enabled=0
		)

		self.assertRaises(frappe.ValidationError, membership.insert)

	def test_owner_membership_cannot_be_demoted(self):
		membership = self.owner_membership(self.create_team())

		membership.team_role = "Viewer"

		self.assertRaises(frappe.ValidationError, membership.save)

	def test_owner_membership_cannot_be_deleted(self):
		membership = self.owner_membership(self.create_team())

		self.assertRaises(frappe.ValidationError, membership.delete)

	def test_non_owner_membership_can_be_deleted(self):
		membership = self.add_member(self.create_team(), self.member, "Manager")

		membership.delete()

		self.assertFalse(frappe.db.exists("Buzz Team Membership", membership.name))

	def test_non_owner_membership_can_be_disabled(self):
		membership = self.add_member(self.create_team(), self.member, "Manager")

		membership.enabled = 0
		membership.save()

		self.assertEqual(frappe.db.get_value("Buzz Team Membership", membership.name, "enabled"), 0)

	def test_duplicate_membership_is_rejected(self):
		team = self.create_team()
		self.add_member(team, self.member, "Manager")

		duplicate = BuzzTeamMembershipFactory.build(team=team, user=self.member, team_role="Viewer")

		self.assertRaises(frappe.ValidationError, duplicate.insert)

	def create_team(self) -> str:
		return BuzzTeamFactory.create_owned_by(self.owner).name

	def add_member(self, team: str, user: str, team_role: str):
		return BuzzTeamMembershipFactory.create(team=team, user=user, team_role=team_role)

	def owner_membership(self, team: str):
		return frappe.get_last_doc("Buzz Team Membership", filters={"team": team, "team_role": "Owner"})


class TestInvitationAccept(IntegrationTestCase):
	def setUp(self):
		# Every invitation mails itself out on insert, which needs an outgoing email account.
		self.enterContext(patch("frappe.sendmail"))
		self.inviter = UserFactory.create_once(INVITER).name
		self.team = BuzzTeamFactory.create_owned_by(self.inviter).name

	def test_invitation_persists_the_team_and_role(self):
		invitation = self.invite("invitee-persisted@example.com")

		stored = frappe.db.get_value(
			"User Invitation", invitation.name, ["buzz_team", "buzz_team_role"], as_dict=True
		)

		self.assertEqual(stored.buzz_team, self.team)
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

		with self.set_user("Guest"):
			invitation.accept(ignore_permissions=True)

		self.assertEqual(len(self.memberships_of(email)), 1)
		self.assertIn("Event Manager", frappe.get_roles(email))

	def test_accept_re_enables_a_disabled_membership(self):
		email = UserFactory.create_once("invitee-disabled@example.com").name
		BuzzTeamMembershipFactory.create(team=self.team, user=email, team_role="Viewer", enabled=0)
		invitation = self.invite(email, "Manager")

		invitation.accept(ignore_permissions=True)

		memberships = self.memberships_of(email)
		self.assertEqual(len(memberships), 1)
		self.assertTrue(memberships[0].enabled)
		self.assertEqual(memberships[0].team_role, "Manager")

	def test_accept_for_an_enabled_member_changes_nothing(self):
		email = UserFactory.create_once("invitee-member@example.com").name
		BuzzTeamMembershipFactory.create(team=self.team, user=email, team_role="Viewer")
		invitation = self.invite(email, "Manager")

		invitation.accept(ignore_permissions=True)

		memberships = self.memberships_of(email)
		self.assertEqual(len(memberships), 1)
		self.assertEqual(memberships[0].team_role, "Viewer")

	def test_accept_is_refused_when_the_inviter_is_not_owner_or_admin(self):
		manager = UserFactory.create_once("invite-manager@example.com").name
		BuzzTeamMembershipFactory.create(team=self.team, user=manager, team_role="Manager")
		email = "invitee-of-manager@example.com"
		invitation = self.invite(email, inviter=manager)

		self.assertRaises(frappe.ValidationError, invitation.accept, True)

		self.assertEqual(self.memberships_of(email), [])

	def test_accept_is_refused_when_the_inviter_left_the_team(self):
		outsider = UserFactory.create_once("invite-outsider@example.com")
		outsider.add_roles("Event Manager")
		email = "invitee-of-outsider@example.com"
		invitation = self.invite(email, inviter=outsider.name)

		self.assertRaises(frappe.ValidationError, invitation.accept, True)

		self.assertEqual(self.memberships_of(email), [])

	def test_accept_is_refused_when_the_invitation_grants_ownership(self):
		email = "invitee-owner@example.com"
		invitation = self.invite(email, "Owner")

		self.assertRaises(frappe.ValidationError, invitation.accept, True)

		self.assertEqual(self.memberships_of(email), [])

	def test_accept_is_refused_when_the_invitation_names_no_team(self):
		invitation = UserInvitationFactory.create()

		self.assertRaises(frappe.ValidationError, invitation.accept, True)

	def test_invitation_to_an_unknown_team_is_rejected_at_invite_time(self):
		self.assertRaises(
			frappe.LinkValidationError, self.invite, "invitee-no-team@example.com", team="No Such Team"
		)

	def invite(
		self, email: str, team_role: str = "Manager", inviter: str | None = None, team: str | None = None
	):
		with self.set_user(inviter or self.inviter):
			invite_by_email(
				emails=email,
				roles=["Buzz User"],
				redirect_to_path="/dashboard",
				app_name="buzz",
				buzz_team=team or self.team,
				buzz_team_role=team_role,
			)
		return frappe.get_last_doc("User Invitation", filters={"email": email})

	def memberships_of(self, user: str) -> list[dict]:
		return frappe.get_all(
			"Buzz Team Membership",
			filters={"team": self.team, "user": user},
			fields=["name", "team_role", "enabled"],
		)


# Kept for the modules that still import it. Use BuzzTeamMembershipFactory instead.
def add_member(team: str, user: str, team_role: str = "Manager") -> "frappe.Document":
	return frappe.get_doc(
		{
			"doctype": "Buzz Team Membership",
			"team": team,
			"user": user,
			"team_role": team_role,
		}
	).insert()
