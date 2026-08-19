from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.teams import get_team_overview, invite_members
from buzz.api.teams.exceptions import CannotGrantOwnership, CannotManageMembers, UnknownTeamRole
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.events.doctype.buzz_team_membership.buzz_team_membership import upsert_membership


class TestInviteMembers(IntegrationTestCase):
	# Rollback is per class, not per test — every test owns its users and its team names.
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		# Every invitation mails itself out on insert, which needs an outgoing email account.
		self.enterContext(patch("frappe.sendmail"))

	def team_owned_by(self, name: str, owner_email: str) -> tuple[str, str]:
		owner = create_user(owner_email, "Owner")
		return create_owned_team(name, owner), owner

	def invitation_for(self, email: str) -> dict:
		return frappe.db.get_value(
			"User Invitation",
			{"email": email},
			["buzz_team", "buzz_team_role", "status"],
			as_dict=True,
		)

	def test_invites_an_email_that_belongs_to_no_user_yet(self):
		team, owner = self.team_owned_by("Invite Newcomer", "invite-owner@example.com")

		frappe.set_user(owner)
		outcomes = invite_members(team, [{"email": "newcomer@example.com", "team_role": "Manager"}])

		self.assertEqual([outcome.status for outcome in outcomes], ["invited"])
		invitation = self.invitation_for("newcomer@example.com")
		self.assertEqual(invitation.buzz_team, team)
		self.assertEqual(invitation.buzz_team_role, "Manager")
		self.assertEqual(invitation.status, "Pending")

	def test_adds_an_existing_user_to_the_team_without_an_invitation(self):
		team, owner = self.team_owned_by("Invite Existing", "invite-owner2@example.com")
		colleague = create_user("invite-colleague@example.com", "Colleague")

		frappe.set_user(owner)
		outcomes = invite_members(team, [{"email": colleague, "team_role": "Frontdesk"}])

		self.assertEqual([outcome.status for outcome in outcomes], ["added"])
		self.assertIsNone(self.invitation_for(colleague))
		membership = frappe.db.get_value(
			"Buzz Team Membership", {"team": team, "user": colleague}, ["team_role", "enabled"], as_dict=True
		)
		self.assertEqual(membership.team_role, "Frontdesk")
		self.assertTrue(membership.enabled)

	def test_a_manager_cannot_invite_anyone(self):
		team, _ = self.team_owned_by("Invite Manager Guard", "invite-owner3@example.com")
		manager = create_user("invite-manager@example.com", "Manager")
		upsert_membership(team, manager, "Manager")

		frappe.set_user(manager)
		with self.assertRaises(CannotManageMembers):
			invite_members(team, [{"email": "manager-invitee@example.com", "team_role": "Viewer"}])

		self.assertIsNone(self.invitation_for("manager-invitee@example.com"))

	def test_a_viewer_cannot_invite_anyone(self):
		team, _ = self.team_owned_by("Invite Viewer Guard", "invite-owner4@example.com")
		viewer = create_user("invite-viewer@example.com", "Viewer")
		upsert_membership(team, viewer, "Viewer")

		frappe.set_user(viewer)
		with self.assertRaises(CannotManageMembers):
			invite_members(team, [{"email": "viewer-invitee@example.com", "team_role": "Viewer"}])

	def test_an_outsider_cannot_invite_anyone(self):
		team, _ = self.team_owned_by("Invite Outsider Guard", "invite-owner5@example.com")
		outsider = create_user("invite-outsider@example.com", "Outsider")

		frappe.set_user(outsider)
		with self.assertRaises(CannotManageMembers):
			invite_members(team, [{"email": "outsider-invitee@example.com", "team_role": "Viewer"}])

	def test_ownership_cannot_be_granted(self):
		team, owner = self.team_owned_by("Invite Ownership", "invite-owner6@example.com")

		frappe.set_user(owner)
		with self.assertRaises(CannotGrantOwnership):
			invite_members(team, [{"email": "would-be-owner@example.com", "team_role": "Owner"}])

		self.assertIsNone(self.invitation_for("would-be-owner@example.com"))

	def test_an_unknown_role_is_rejected(self):
		team, owner = self.team_owned_by("Invite Unknown Role", "invite-owner7@example.com")

		frappe.set_user(owner)
		with self.assertRaises(UnknownTeamRole):
			invite_members(team, [{"email": "bad-role@example.com", "team_role": "Overlord"}])

	def test_an_existing_member_is_left_alone(self):
		team, owner = self.team_owned_by("Invite Existing Member", "invite-owner8@example.com")
		member = create_user("invite-settled@example.com", "Settled")
		upsert_membership(team, member, "Viewer")

		frappe.set_user(owner)
		outcomes = invite_members(team, [{"email": member, "team_role": "Admin"}])

		self.assertEqual([outcome.status for outcome in outcomes], ["already_a_member"])
		self.assertEqual(
			frappe.db.get_value("Buzz Team Membership", {"team": team, "user": member}, "team_role"),
			"Viewer",
		)

	def test_a_removed_member_is_re_enabled_rather_than_invited(self):
		team, owner = self.team_owned_by("Invite Returning", "invite-owner9@example.com")
		member = create_user("invite-returning@example.com", "Returning")
		upsert_membership(team, member, "Manager")
		frappe.db.set_value("Buzz Team Membership", {"team": team, "user": member}, "enabled", 0)

		frappe.set_user(owner)
		outcomes = invite_members(team, [{"email": member, "team_role": "Frontdesk"}])

		self.assertEqual([outcome.status for outcome in outcomes], ["added"])
		self.assertIsNone(self.invitation_for(member))

	def test_an_existing_user_is_matched_regardless_of_case(self):
		team, owner = self.team_owned_by("Invite Mixed Case", "invite-owner10@example.com")
		colleague = create_user("invite-mixedcase@example.com", "Mixed")

		frappe.set_user(owner)
		outcomes = invite_members(team, [{"email": "Invite-MixedCase@Example.com", "team_role": "Viewer"}])

		self.assertEqual([outcome.status for outcome in outcomes], ["added"])
		self.assertTrue(frappe.db.exists("Buzz Team Membership", {"team": team, "user": colleague}))

	def test_names_the_person_who_was_added(self):
		team, owner = self.team_owned_by("Invite Named", "invite-owner11@example.com")
		colleague = create_user("invite-named@example.com", "Rhea")

		frappe.set_user(owner)
		outcomes = invite_members(team, [{"email": colleague, "team_role": "Manager"}])

		self.assertEqual(outcomes[0].full_name, "Rhea")

	def test_an_invited_stranger_has_no_name_to_show_yet(self):
		team, owner = self.team_owned_by("Invite Nameless", "invite-owner12@example.com")

		frappe.set_user(owner)
		outcomes = invite_members(team, [{"email": "nameless@example.com", "team_role": "Viewer"}])

		self.assertIsNone(outcomes[0].full_name)


class TestTeamOverviewInvitations(IntegrationTestCase):
	# Rollback is per class, not per test — every test owns its users and its team names.
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		# Every invitation mails itself out on insert, which needs an outgoing email account.
		self.enterContext(patch("frappe.sendmail"))

	def test_lists_the_teams_pending_invitations(self):
		owner = create_user("overview-invites-owner@example.com", "Owner")
		team = create_owned_team("Overview Invites", owner)

		frappe.set_user(owner)
		invite_members(team, [{"email": "awaited@example.com", "team_role": "Frontdesk"}])
		invites = get_team_overview(team).invites

		self.assertEqual(len(invites), 1)
		self.assertEqual(invites[0].email, "awaited@example.com")
		self.assertEqual(invites[0].team_role, "Frontdesk")

	def test_leaves_out_another_teams_invitations(self):
		owner = create_user("overview-invites-mine@example.com", "Owner")
		mine = create_owned_team("Overview Invites Mine", owner)
		theirs = create_owned_team(
			"Overview Invites Theirs", create_user("overview-invites-other@example.com", "Other")
		)

		frappe.set_user(owner)
		invite_members(mine, [{"email": "mine@example.com", "team_role": "Viewer"}])
		frappe.set_user("Administrator")
		invite_members(theirs, [{"email": "theirs@example.com", "team_role": "Viewer"}])

		frappe.set_user(owner)
		self.assertEqual([invite.email for invite in get_team_overview(mine).invites], ["mine@example.com"])

	def test_drops_an_invitation_once_it_is_no_longer_pending(self):
		owner = create_user("overview-invites-settled@example.com", "Owner")
		team = create_owned_team("Overview Invites Settled", owner)

		frappe.set_user(owner)
		invite_members(team, [{"email": "cancelled@example.com", "team_role": "Viewer"}])
		frappe.set_user("Administrator")
		frappe.db.set_value("User Invitation", {"email": "cancelled@example.com"}, "status", "Cancelled")

		frappe.set_user(owner)
		self.assertEqual(get_team_overview(team).invites, [])
