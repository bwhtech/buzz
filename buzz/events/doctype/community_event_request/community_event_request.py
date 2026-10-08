# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buzz.permissions import WRITE_PTYPES, as_sql, is_unrestricted, my_teams, team_role_of


class CommunityEventRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		community: DF.Link
		event: DF.Link
		event_team: DF.Link | None
		event_title: DF.Data | None
		review_note: DF.SmallText | None
		reviewed_by: DF.Link | None
		status: DF.Literal["Pending", "Approved", "Rejected"]
		submitted_by: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.event_title, self.event_team = frappe.db.get_value("Buzz Event", self.event, ["title", "team"])
		# An unpublished event may still be taken off the page.
		if self.status != "Rejected":
			self.validate_event()
		self.validate_community()
		self.validate_unique_pair()

	def validate_event(self):
		if not frappe.db.get_value("Buzz Event", self.event, "is_published"):
			frappe.throw(_("Only a published event can be listed by a community."))

	def validate_community(self):
		community = frappe.db.get_value(
			"Buzz Team", self.community, ["accept_community_submissions", "is_published"], as_dict=True
		)
		if not (community and community.accept_community_submissions and community.is_published):
			frappe.throw(_("{0} is not a published community.").format(self.community))
		if self.community == self.event_team:
			frappe.throw(_("A community lists its own events already."))

	def validate_unique_pair(self):
		pair = {"event": self.event, "community": self.community, "name": ["!=", self.name]}
		if frappe.db.exists("Community Event Request", pair):
			frappe.throw(
				_("This event already has a request with this community."), frappe.DuplicateEntryError
			)


def on_doctype_update():
	# validate_unique_pair names the clash; the index stops two concurrent inserts.
	frappe.db.add_unique("Community Event Request", ["event", "community"])


def has_request_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	"""Members of either team read a request; changes go through buzz.api.communities."""
	user = user or frappe.session.user
	if is_unrestricted(user):
		return True
	if ptype in WRITE_PTYPES:
		return False
	return bool(team_role_of(user, doc.event_team) or team_role_of(user, doc.community))


def request_query_conditions(user: str | None = None, **kwargs) -> str | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None
	table = frappe.qb.DocType("Community Event Request")
	return as_sql(table.event_team.isin(my_teams(user)) | table.community.isin(my_teams(user)))
