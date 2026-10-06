from unittest.mock import patch

import frappe
from frappe.apps import get_default_path
from frappe.tests import IntegrationTestCase

from buzz.api.teams import get_team_overview, invite_members, resend_invite, retract_invite
from buzz.api.teams.exceptions import (
	CannotGrantOwnership,
	CannotManageMembers,
	NoPendingInvite,
	UnknownTeamRole,
)
from buzz.tests.factories import BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory
from buzz.tests.factories.core.user_invitation_factory import UserInvitationFactory


class InvitationTestCase(IntegrationTestCase):
	# Rollback is per class, not per test — every test owns its users and its invitees.
	def setUp(self):
		# Every invitation mails itself out on insert, which needs an outgoing email account.
		self.enterContext(patch("frappe.sendmail"))

	def user(self, email: str) -> str:
		return UserFactory.create_once(email).name

	def team_owned_by(self, owner_email: str) -> tuple[str, str]:
		owner = self.user(owner_email)
		return BuzzTeamFactory.create_owned_by(owner).name, owner

	def add_member(self, team: str, user: str, team_role: str, **overrides):
		BuzzTeamMembershipFactory.create(team=team, user=user, team_role=team_role, **overrides)


class TestInviteMembers(InvitationTestCase):
	def test_invites_an_email_that_belongs_to_no_user_yet(self):
		team, owner = self.team_owned_by("invite-owner@example.com")

		outcomes = self.invite_as(owner, team, "newcomer@example.com", "Manager")

		self.assertEqual([outcome.status for outcome in outcomes], ["invited"])
		invitation = self.invitation_for("newcomer@example.com")
		self.assertEqual(invitation.buzz_team, team)
		self.assertEqual(invitation.buzz_team_role, "Manager")
		self.assertEqual(invitation.status, "Pending")

	def test_adds_an_existing_user_to_the_team_without_an_invitation(self):
		team, owner = self.team_owned_by("invite-owner2@example.com")
		colleague = self.user("invite-colleague@example.com")

		outcomes = self.invite_as(owner, team, colleague, "Frontdesk")

		self.assertEqual([outcome.status for outcome in outcomes], ["added"])
		self.assertIsNone(self.invitation_for(colleague))
		membership = frappe.db.get_value(
			"Buzz Team Membership", {"team": team, "user": colleague}, ["team_role", "enabled"], as_dict=True
		)
		self.assertEqual(membership.team_role, "Frontdesk")
		self.assertTrue(membership.enabled)

	def test_a_manager_cannot_invite_anyone(self):
		team, _ = self.team_owned_by("invite-owner3@example.com")
		manager = self.user("invite-manager@example.com")
		self.add_member(team, manager, "Manager")

		with self.assertRaises(CannotManageMembers):
			self.invite_as(manager, team, "manager-invitee@example.com", "Viewer")

		self.assertIsNone(self.invitation_for("manager-invitee@example.com"))

	def test_a_viewer_cannot_invite_anyone(self):
		team, _ = self.team_owned_by("invite-owner4@example.com")
		viewer = self.user("invite-viewer@example.com")
		self.add_member(team, viewer, "Viewer")

		with self.assertRaises(CannotManageMembers):
			self.invite_as(viewer, team, "viewer-invitee@example.com", "Viewer")

	def test_an_outsider_cannot_invite_anyone(self):
		team, _ = self.team_owned_by("invite-owner5@example.com")
		outsider = self.user("invite-outsider@example.com")

		with self.assertRaises(CannotManageMembers):
			self.invite_as(outsider, team, "outsider-invitee@example.com", "Viewer")

	def test_ownership_cannot_be_granted(self):
		team, owner = self.team_owned_by("invite-owner6@example.com")

		with self.assertRaises(CannotGrantOwnership):
			self.invite_as(owner, team, "would-be-owner@example.com", "Owner")

		self.assertIsNone(self.invitation_for("would-be-owner@example.com"))

	def test_an_unknown_role_is_rejected(self):
		team, owner = self.team_owned_by("invite-owner7@example.com")

		with self.assertRaises(UnknownTeamRole):
			self.invite_as(owner, team, "bad-role@example.com", "Overlord")

	def test_an_existing_member_is_left_alone(self):
		team, owner = self.team_owned_by("invite-owner8@example.com")
		member = self.user("invite-settled@example.com")
		self.add_member(team, member, "Viewer")

		outcomes = self.invite_as(owner, team, member, "Admin")

		self.assertEqual([outcome.status for outcome in outcomes], ["already_a_member"])
		self.assertEqual(
			frappe.db.get_value("Buzz Team Membership", {"team": team, "user": member}, "team_role"),
			"Viewer",
		)

	def test_a_removed_member_is_re_enabled_rather_than_invited(self):
		team, owner = self.team_owned_by("invite-owner9@example.com")
		member = self.user("invite-returning@example.com")
		self.add_member(team, member, "Manager", enabled=0)

		outcomes = self.invite_as(owner, team, member, "Frontdesk")

		self.assertEqual([outcome.status for outcome in outcomes], ["added"])
		self.assertIsNone(self.invitation_for(member))

	def test_an_existing_user_is_matched_regardless_of_case(self):
		team, owner = self.team_owned_by("invite-owner10@example.com")
		colleague = self.user("invite-mixedcase@example.com")

		outcomes = self.invite_as(owner, team, "Invite-MixedCase@Example.com", "Viewer")

		self.assertEqual([outcome.status for outcome in outcomes], ["added"])
		self.assertTrue(frappe.db.exists("Buzz Team Membership", {"team": team, "user": colleague}))

	def test_names_the_person_who_was_added(self):
		team, owner = self.team_owned_by("invite-owner11@example.com")
		colleague = UserFactory.create(first_name="Rhea", last_name="").name

		outcomes = self.invite_as(owner, team, colleague, "Manager")

		self.assertEqual(outcomes[0].full_name, "Rhea")

	def test_an_invited_stranger_has_no_name_to_show_yet(self):
		team, owner = self.team_owned_by("invite-owner12@example.com")

		outcomes = self.invite_as(owner, team, "nameless@example.com", "Viewer")

		self.assertIsNone(outcomes[0].full_name)

	def invite_as(self, user: str, team: str, email: str, team_role: str) -> list:
		with self.set_user(user):
			return invite_members(team, [{"email": email, "team_role": team_role}])

	def invitation_for(self, email: str) -> dict:
		return frappe.db.get_value(
			"User Invitation",
			{"email": email},
			["buzz_team", "buzz_team_role", "status"],
			as_dict=True,
		)


class TestTeamOverviewInvitations(InvitationTestCase):
	def test_lists_the_teams_pending_invitations(self):
		team, owner = self.team_owned_by("overview-invites-owner@example.com")

		with self.set_user(owner):
			invite_members(team, [{"email": "awaited@example.com", "team_role": "Frontdesk"}])
			invites = get_team_overview(team).invites

		self.assertEqual(len(invites), 1)
		self.assertEqual(invites[0].email, "awaited@example.com")
		self.assertEqual(invites[0].team_role, "Frontdesk")

	def test_leaves_out_another_teams_invitations(self):
		mine, owner = self.team_owned_by("overview-invites-mine@example.com")
		theirs, _ = self.team_owned_by("overview-invites-other@example.com")
		self.invite_to(mine, "mine@example.com")
		self.invite_to(theirs, "theirs@example.com")

		with self.set_user(owner):
			invites = get_team_overview(mine).invites

		self.assertEqual([invite.email for invite in invites], ["mine@example.com"])

	def test_drops_an_invitation_once_it_is_no_longer_pending(self):
		team, owner = self.team_owned_by("overview-invites-settled@example.com")
		invitation = self.invite_to(team, "cancelled@example.com")
		frappe.db.set_value("User Invitation", invitation, "status", "Cancelled")

		with self.set_user(owner):
			self.assertEqual(get_team_overview(team).invites, [])

	def invite_to(self, team: str, email: str) -> str:
		return UserInvitationFactory.create(email=email, buzz_team=team, buzz_team_role="Viewer").name


class TestInviteActions(InvitationTestCase):
	def test_resending_rotates_the_key_and_leaves_the_invitation_pending(self):
		team, owner = self.invited_team("resend-owner@example.com", "resend-me@example.com")
		before = self.invitation_for("resend-me@example.com")

		with self.set_user(owner):
			resend_invite(team, "resend-me@example.com")

		after = self.invitation_for("resend-me@example.com")
		self.assertEqual(after.status, "Pending")
		# The plaintext key only ever exists in the mail, so a new hash is the proof.
		self.assertNotEqual(after.key, before.key)

	def test_retracting_cancels_the_invitation_and_drops_it_from_the_overview(self):
		team, owner = self.invited_team("retract-owner@example.com", "retract-me@example.com")

		with self.set_user(owner):
			retract_invite(team, "retract-me@example.com")
			invites = get_team_overview(team).invites

		self.assertEqual(self.invitation_for("retract-me@example.com").status, "Cancelled")
		self.assertEqual(invites, [])

	def test_an_address_is_matched_regardless_of_case_or_padding(self):
		team, owner = self.invited_team("untidy-owner@example.com", "untidy@example.com")

		with self.set_user(owner):
			retract_invite(team, "  Untidy@Example.com  ")

		self.assertEqual(self.invitation_for("untidy@example.com").status, "Cancelled")

	def test_a_manager_can_do_neither(self):
		team, _ = self.invited_team("actions-owner2@example.com", "guarded@example.com")
		manager = self.user("actions-manager@example.com")
		self.add_member(team, manager, "Manager")

		with self.set_user(manager):
			with self.assertRaises(CannotManageMembers):
				resend_invite(team, "guarded@example.com")
			with self.assertRaises(CannotManageMembers):
				retract_invite(team, "guarded@example.com")

		self.assertEqual(self.invitation_for("guarded@example.com").status, "Pending")

	def test_another_teams_owner_can_do_neither(self):
		team, _ = self.invited_team("actions-owner3@example.com", "not-yours@example.com")
		_, outsider = self.team_owned_by("actions-other-owner@example.com")

		# Core's own guards are app-wide: an Event Manager passes them for any buzz invitation.
		with self.set_user(outsider):
			with self.assertRaises(CannotManageMembers):
				resend_invite(team, "not-yours@example.com")
			with self.assertRaises(CannotManageMembers):
				retract_invite(team, "not-yours@example.com")

		self.assertEqual(self.invitation_for("not-yours@example.com").status, "Pending")

	def test_an_unknown_address_has_nothing_to_act_on(self):
		team, owner = self.invited_team("actions-owner4@example.com", "known@example.com")

		with self.set_user(owner), self.assertRaises(NoPendingInvite):
			resend_invite(team, "stranger@example.com")

	def test_a_retracted_invitation_cannot_be_retracted_again(self):
		team, owner = self.invited_team("actions-owner5@example.com", "twice@example.com")

		with self.set_user(owner):
			retract_invite(team, "twice@example.com")

			with self.assertRaises(NoPendingInvite):
				retract_invite(team, "twice@example.com")
			with self.assertRaises(NoPendingInvite):
				resend_invite(team, "twice@example.com")

	def invited_team(self, owner_email: str, invitee: str) -> tuple[str, str]:
		"""A team with one pending invitation, and the owner who sent it."""
		team, owner = self.team_owned_by(owner_email)
		with self.set_user(owner):
			invite_members(team, [{"email": invitee, "team_role": "Viewer"}])
		return team, owner

	def invitation_for(self, email: str) -> dict:
		return frappe.db.get_value(
			"User Invitation", {"email": email}, ["name", "key", "status"], as_dict=True
		)


class TestDefaultPath(IntegrationTestCase):
	def test_an_invitee_setting_their_password_lands_on_the_dashboard(self):
		# Core sends a System User to `get_default_path()` after a password reset, ignoring
		# the invitation's own redirect. Buzz roles have no desk access, so that path has to
		# be the dashboard.
		self.assertEqual(get_default_path(), "/b")
