import re
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime

from buzz.api.events.collaborators import (
	accept_collaborator_invite,
	has_collaborations,
	invite_collaborators,
	revoke_collaborators,
	update_collaborator_access,
)
from buzz.api.events.exceptions import (
	AlreadyCollaborator,
	AlreadyOnTeam,
	CannotManageEvent,
	CollaboratorLoginRequired,
	CollaboratorWrongAccount,
	InvalidCollaboratorInvitation,
	InvalidSectionAccess,
)
from buzz.permissions import get_section_access
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import BuzzEventCollaboratorFactory, BuzzTeamMembershipFactory, UserFactory
from buzz.tests.utils import html_part, mute_outgoing_email

COLLABORATOR = "Buzz Event Collaborator"
LOG_IN = "buzz.api.events.collaborators.log_in_as"
KEY_PATTERN = r"key=([0-9a-f]+)"


class CollaboratorInviteTestCase(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = UserFactory.create_once("invite-manager@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.manager, team_role="Manager")
		cls.event = str(cls.event_a)

	def setUp(self):
		super().setUp()
		mute_outgoing_email(self)

	def invite(self, email: str, as_user: str | None = None, **sections):
		with self.set_user(as_user or self.alice):
			return invite_collaborators(self.event, [{"email": email, "guests_access": "View"} | sections])

	def row(self, email: str):
		return frappe.get_doc(COLLABORATOR, {"event": self.event_a, "email": email})

	def emails_to(self, email: str) -> list:
		return frappe.get_all(
			"Email Queue Recipient", filters={"recipient": email}, pluck="parent", order_by="creation asc"
		)

	def key_from_mail(self, email: str) -> str:
		message = frappe.get_doc("Email Queue", self.emails_to(email)[-1]).message
		return re.search(KEY_PATTERN, html_part(message)).group(1)


class TestInvite(CollaboratorInviteTestCase):
	def test_owner_invite_creates_a_pending_row_and_one_email(self):
		self.invite("invitee-one@example.com")

		row = self.row("invitee-one@example.com")
		self.assertEqual((row.status, row.guests_access, row.details_access), ("Pending", "View", "View"))
		self.assertEqual(row.invited_by, self.alice)
		self.assertEqual(len(self.emails_to("invitee-one@example.com")), 1)

	def test_manager_collaborator_and_outsider_cannot_invite(self):
		collaborator = BuzzEventCollaboratorFactory.create(
			"accepted", event=self.event_a, email="inv-c@example.com", guests_access="View"
		)
		for user in (self.manager, collaborator.user, self.outsider):
			with self.subTest(user=user), self.assertRaises(CannotManageEvent):
				self.invite("nobody@example.com", as_user=user)

	def test_inviting_a_team_member_is_refused(self):
		with self.assertRaises(AlreadyOnTeam):
			self.invite(self.manager)

	def test_inviting_an_accepted_collaborator_is_refused(self):
		BuzzEventCollaboratorFactory.create(
			"accepted", event=self.event_a, email="inv-acc@example.com", guests_access="View"
		)

		with self.assertRaises(AlreadyCollaborator):
			self.invite("inv-acc@example.com")

	def test_reinviting_rotates_the_key(self):
		self.invite("invitee-two@example.com")
		old_key = self.key_from_mail("invitee-two@example.com")

		self.invite("invitee-two@example.com", guests_access="Edit")

		new_key = self.key_from_mail("invitee-two@example.com")
		self.assertNotEqual(old_key, new_key)
		self.assertEqual(self.row("invitee-two@example.com").guests_access, "Edit")
		with self.assertRaises(InvalidCollaboratorInvitation):
			accept_collaborator_invite(old_key)

	def test_invalid_level_is_refused(self):
		with self.assertRaises(InvalidSectionAccess):
			self.invite("invitee-bad@example.com", guests_access="Owner")
		with self.assertRaises(InvalidSectionAccess):
			self.invite("invitee-bad@example.com", details_access="")

	def test_revoke_and_access_change_need_team_admin(self):
		BuzzEventCollaboratorFactory.create(
			"accepted", event=self.event_a, email="inv-r@example.com", guests_access="View"
		)
		with self.set_user(self.manager):
			with self.assertRaises(CannotManageEvent):
				revoke_collaborators(self.event, ["inv-r@example.com"])
			with self.assertRaises(CannotManageEvent):
				update_collaborator_access(self.event, "inv-r@example.com", {"guests_access": "Edit"})

	def test_has_collaborations_is_true_for_accepted_collaborators_only(self):
		accepted = BuzzEventCollaboratorFactory.create(
			"accepted", event=self.event_a, email="inv-h@example.com", guests_access="View"
		)
		BuzzEventCollaboratorFactory.create(
			"pending", event=self.event_a, email="inv-p@example.com", guests_access="View"
		)

		with self.set_user(accepted.user):
			self.assertTrue(has_collaborations())
		with self.set_user(self.outsider):
			self.assertFalse(has_collaborations())

	def test_access_change_updates_the_sections(self):
		BuzzEventCollaboratorFactory.create(
			"accepted", event=self.event_a, email="inv-u@example.com", guests_access="View"
		)
		user = frappe.db.get_value(COLLABORATOR, {"email": "inv-u@example.com"}, "user")

		with self.set_user(self.alice):
			update_collaborator_access(
				self.event, "inv-u@example.com", {"guests_access": "Edit", "talks_access": "View"}
			)

		access = get_section_access(user, self.event_a)
		self.assertEqual((access["guests"], access["talks"], access["sponsors"]), ("Edit", "View", None))

	def test_revoke_clears_key_and_access(self):
		self.invite("invitee-rev@example.com")
		key = self.key_from_mail("invitee-rev@example.com")

		with self.set_user(self.alice):
			revoke_collaborators(self.event, ["invitee-rev@example.com"])

		row = self.row("invitee-rev@example.com")
		self.assertEqual((row.status, row.invite_key_hash), ("Revoked", None))
		with self.assertRaises(InvalidCollaboratorInvitation):
			accept_collaborator_invite(key)


class TestAccept(CollaboratorInviteTestCase):
	def invite_and_key(self, email: str) -> str:
		if email.startswith("existing"):
			UserFactory.create_once(email)
		self.invite(email, guests_access="Edit")
		return self.key_from_mail(email)

	def test_logged_in_invitee_accepts(self):
		email = "existing-accept@example.com"
		key = self.invite_and_key(email)

		with self.set_user(email):
			result = accept_collaborator_invite(key)

		row = self.row(email)
		self.assertEqual((row.status, row.user, row.invite_key_hash), ("Accepted", email, None))
		self.assertEqual(result.redirect_to, f"/b/manage/events/{self.event}")
		self.assertEqual(get_section_access(email, self.event_a)["guests"], "Edit")
		self.assertIn("Frontdesk Manager", frappe.get_roles(email))

	def test_another_logged_in_user_is_refused(self):
		key = self.invite_and_key("existing-other@example.com")

		with self.set_user(self.outsider), self.assertRaises(CollaboratorWrongAccount):
			accept_collaborator_invite(key)

		self.assertEqual(self.row("existing-other@example.com").status, "Pending")

	def test_guest_with_an_existing_account_must_log_in(self):
		key = self.invite_and_key("existing-guest@example.com")

		with self.set_user("Guest"), patch(LOG_IN) as log_in:
			with self.assertRaises(CollaboratorLoginRequired):
				accept_collaborator_invite(key)

		log_in.assert_not_called()
		self.assertEqual(self.row("existing-guest@example.com").status, "Pending")

	def test_guest_with_a_new_email_gets_an_account(self):
		email = "brand-new-collaborator@example.com"
		self.assertFalse(frappe.db.exists("User", email))
		key = self.invite_and_key(email)

		with (
			self.set_user("Guest"),
			self.change_settings("System Settings", disable_user_pass_login=1),
			patch(LOG_IN) as log_in,
		):
			accept_collaborator_invite(key)

		log_in.assert_called_once_with(email)
		self.assertEqual(self.row(email).status, "Accepted")
		self.assertIn("Buzz User", frappe.get_roles(email))

	def test_new_account_with_password_login_is_sent_to_set_a_password(self):
		email = "brand-new-password@example.com"
		key = self.invite_and_key(email)

		with (
			self.set_user("Guest"),
			self.change_settings("System Settings", disable_user_pass_login=0),
			patch(LOG_IN) as log_in,
		):
			result = accept_collaborator_invite(key)

		log_in.assert_not_called()
		self.assertIn("update-password", result.redirect_to)

	def test_expired_invitation_is_refused(self):
		email = "existing-expired@example.com"
		key = self.invite_and_key(email)
		stale = now_datetime() - timedelta(days=30)
		frappe.db.set_value(COLLABORATOR, self.row(email).name, "invited_at", stale)

		with self.set_user(email), self.assertRaises(InvalidCollaboratorInvitation):
			accept_collaborator_invite(key)

	def test_inviter_who_lost_admin_cannot_have_the_invite_accepted(self):
		admin = UserFactory.create_once("invite-demoted@example.com").name
		membership = BuzzTeamMembershipFactory.create(team=self.team_a, user=admin, team_role="Admin")
		email = "existing-demoted@example.com"
		UserFactory.create_once(email)
		self.invite(email, as_user=admin)
		key = self.key_from_mail(email)

		membership.team_role = "Viewer"
		membership.save()

		with self.set_user(email), self.assertRaises(InvalidCollaboratorInvitation):
			accept_collaborator_invite(key)

	def test_unknown_key_is_refused(self):
		with self.assertRaises(InvalidCollaboratorInvitation):
			accept_collaborator_invite("not-a-key")
		with self.assertRaises(InvalidCollaboratorInvitation):
			accept_collaborator_invite("")
