# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists


def create_default_team_for(user: str) -> "BuzzTeam":
	"""Give a user a team of their own. Idempotent."""
	owned = frappe.db.get_value(
		"Buzz Team Membership", {"user": user, "team_role": "Owner", "enabled": 1}, "team"
	)
	if owned:
		return frappe.get_doc("Buzz Team", owned)

	first_name = frappe.db.get_value("User", user, "first_name") or user
	team = frappe.get_doc({"doctype": "Buzz Team", "team_name": f"{first_name}'s Team"})
	# The patch creates teams for other users, so the owner cannot come from the session.
	team.flags.owner_user = user
	return team.insert(ignore_permissions=True)


class BuzzTeam(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		logo: DF.AttachImage | None
		slug: DF.Data | None
		team_name: DF.Data
	# end: auto-generated types

	def validate(self):
		if not self.slug:
			self.set_slug()

	def set_slug(self):
		slug = frappe.website.utils.cleanup_page_name(self.team_name).replace("_", "-")
		# Two users called Sam both want "sams-team", and the column is unique.
		self.slug = append_number_if_name_exists("Buzz Team", slug, fieldname="slug")

	def after_insert(self):
		frappe.get_doc(
			{
				"doctype": "Buzz Team Membership",
				"team": self.name,
				"user": self.flags.owner_user or frappe.session.user,
				"team_role": "Owner",
			}
		).insert(ignore_permissions=True)
