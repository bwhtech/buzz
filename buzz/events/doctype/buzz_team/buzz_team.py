# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists

from buzz.events.doctype.buzz_team_membership.buzz_team_membership import upsert_membership
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import create_team_settings
from buzz.permissions import can_manage_members, my_team_names

SEARCH_LIMIT = 10
STANDARD_USERS = ("Administrator", "Guest")


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


def set_team_from_sole_membership(doc, event=None):
	"""Fill an empty team from the user's only enabled membership.

	Zero or several memberships leave it empty, so reqd raises rather than this
	picking a team on the user's behalf.
	"""
	if doc.team:
		return

	teams = my_team_names(frappe.session.user)
	if len(teams) == 1:
		doc.team = teams[0]


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

	def onload(self):
		self.set_onload("can_manage_members", can_manage_members(self.name))

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
		create_team_settings(self.name)

	@frappe.whitelist()
	def search_addable_users(self, txt: str = "") -> list[dict]:
		"""Users who could still join this team, matched on email or full name.

		Website users are in on purpose: frappe's own `user_query` hides them, but an attendee
		is as likely to be a colleague as anyone. Adding one to a team grants a role with desk
		access, which turns them into a System User.
		"""
		self.check_can_manage_members()

		pattern = f"%{txt}%"
		users = frappe.get_all(
			"User",
			filters=[
				["enabled", "=", 1],
				["name", "not in", [*STANDARD_USERS, *self.member_users()]],
			],
			or_filters=[["name", "like", pattern], ["full_name", "like", pattern]],
			fields=["name", "full_name"],
			order_by="full_name asc",
			limit_page_length=SEARCH_LIMIT,
		)
		return [{"value": user.name, "description": user.full_name} for user in users]

	def member_users(self) -> list[str]:
		return frappe.get_all("Buzz Team Membership", filters={"team": self.name, "enabled": 1}, pluck="user")

	def check_can_manage_members(self):
		if not can_manage_members(self.name):
			frappe.throw(_("You cannot manage members of this team."), frappe.PermissionError)

	@frappe.whitelist()
	def add_members(self, members: str) -> int:
		"""Put existing users on this team. Returns how many of them were newly added."""
		self.check_can_manage_members()

		added = [
			member.get("user")
			for member in parse_members(members)
			# upsert_membership inserts with ignore_permissions, hence the guard above.
			if upsert_membership(self.name, member.get("user"), member.get("team_role"))
		]
		for user in added:
			self.send_added_mail(user)
		return len(added)

	def send_added_mail(self, user: str):
		frappe.sendmail(
			recipients=[user],
			subject=_("You have been added to {0}").format(self.team_name),
			message=_("<p>You are now a member of <strong>{0}</strong> on Buzz.</p>").format(self.team_name),
			reference_doctype=self.doctype,
			reference_name=self.name,
		)


def parse_members(members: str) -> list[dict]:
	"""Rows of {user, team_role} as the form sends them."""
	rows = frappe.parse_json(members)
	if any(row.get("team_role") == "Owner" for row in rows):
		frappe.throw(_("Ownership of a team cannot be granted."))
	return rows
