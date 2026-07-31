# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# Viewer earns nothing. "Buzz User" is granted by buzz.utils.add_buzz_user_role instead.
TEAM_ROLE_TO_FRAPPE_ROLE = {
	"Owner": "Event Manager",
	"Admin": "Event Manager",
	"Manager": "Event Manager",
	"Frontdesk": "Frontdesk Manager",
}
MANAGED_FRAPPE_ROLES = set(TEAM_ROLE_TO_FRAPPE_ROLE.values())


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
		# "one enabled Owner must remain" when transfer is needed.
		previous = self.get_doc_before_save()
		was_owner = previous is not None and previous.team_role == "Owner"

		if (was_owner or self.team_role == "Owner") and not self.enabled:
			frappe.throw(_("The owner of a team cannot be disabled."))

		if was_owner and self.team_role != "Owner":
			frappe.throw(_("The owner of a team cannot be given another role."))
