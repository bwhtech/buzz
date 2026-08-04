# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document

if TYPE_CHECKING:
	from frappe.core.doctype.user.user import User
	from frappe.core.doctype.user_invitation.user_invitation import UserInvitation

# Viewer earns nothing. "Buzz User" is granted by buzz.utils.add_buzz_user_role instead.
TEAM_ROLE_TO_FRAPPE_ROLE = {
	"Owner": "Event Manager",
	"Admin": "Event Manager",
	"Manager": "Event Manager",
	"Frontdesk": "Frontdesk Manager",
}
MANAGED_FRAPPE_ROLES = set(TEAM_ROLE_TO_FRAPPE_ROLE.values())
INVITING_TEAM_ROLES = ("Owner", "Admin")


def on_invitation_accepted(invitation: "UserInvitation", user: "User", user_inserted: bool) -> None:
	"""Turn an accepted `User Invitation` into a team membership.

	Every accepted invitation routes through here, whoever created it, so the inviter's
	authority is checked here rather than at invite time.
	"""
	team, team_role = invitation.buzz_team, invitation.buzz_team_role
	if not team or not team_role:
		frappe.throw(_("This invitation is not linked to a team."))

	if team_role == "Owner":
		frappe.throw(_("An invitation cannot grant ownership of a team."))

	inviter_role = frappe.db.get_value(
		"Buzz Team Membership", {"team": team, "user": invitation.invited_by, "enabled": 1}, "team_role"
	)
	if inviter_role not in INVITING_TEAM_ROLES:
		frappe.throw(_("{0} cannot invite members to this team.").format(invitation.invited_by))

	upsert_membership(team, user.name, team_role)


def upsert_membership(team: str, user: str, team_role: str) -> None:
	"""Re-enable a lapsed membership rather than adding a second one. Enabled ones are left alone."""
	name = frappe.db.exists("Buzz Team Membership", {"team": team, "user": user})
	if not name:
		frappe.get_doc(
			{"doctype": "Buzz Team Membership", "team": team, "user": user, "team_role": team_role}
		).insert(ignore_permissions=True)
		return

	membership = frappe.get_doc("Buzz Team Membership", name)
	if membership.enabled:
		return

	membership.enabled = 1
	membership.team_role = team_role
	membership.save(ignore_permissions=True)


def sync_frappe_roles(user: str):
	"""Recompute a user's managed roles across every enabled membership.

	Recomputed, not incremented: losing one membership must not remove a role another earns.
	"""
	team_roles = frappe.get_all(
		"Buzz Team Membership",
		filters={"user": user, "enabled": 1},
		pluck="team_role",
	)
	earned = {
		TEAM_ROLE_TO_FRAPPE_ROLE[team_role]
		for team_role in team_roles
		if team_role in TEAM_ROLE_TO_FRAPPE_ROLE
	}

	user_doc = frappe.get_doc("User", user)
	# Roles follow from the membership, not from whoever triggered the save — a team admin
	# adding a member, or a Guest accepting an invitation, has no write access to User.
	user_doc.flags.ignore_permissions = True
	user_doc.add_roles(*earned)
	user_doc.remove_roles(*(MANAGED_FRAPPE_ROLES - earned))


class BuzzTeamMembership(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		team: DF.Link
		team_role: DF.Literal["Owner", "Admin", "Manager", "Frontdesk", "Viewer"]
		user: DF.Link
	# end: auto-generated types

	def on_update(self):
		# Fires on insert too — Document._action is "save" for both.
		sync_frappe_roles(self.user)

	def on_trash(self):
		if self.team_role == "Owner":
			frappe.throw(_("The owner of a team cannot be removed."))

	def after_delete(self):
		# Not on_trash — that runs before the row is gone, so it would still be counted.
		sync_frappe_roles(self.user)

	def validate(self):
		self.validate_duplicate()
		self.validate_owner_is_locked()

	def validate_duplicate(self):
		existing = frappe.db.exists(
			"Buzz Team Membership",
			{"team": self.team, "user": self.user, "name": ("!=", self.name)},
		)
		if existing:
			frappe.throw(_("{0} is already a member of this team.").format(self.user))

	def validate_owner_is_locked(self):
		# Locking the row outright means ownership can never be transferred. Relax to
		# "one enabled Owner must remain" here and in on_trash when transfer is needed.
		previous = self.get_doc_before_save()
		was_owner = previous is not None and previous.team_role == "Owner"

		if (was_owner or self.team_role == "Owner") and not self.enabled:
			frappe.throw(_("The owner of a team cannot be disabled."))

		if was_owner and self.team_role != "Owner":
			frappe.throw(_("The owner of a team cannot be given another role."))
