# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, validate_url

from buzz.permissions import WRITE_PTYPES, as_sql, is_unrestricted, my_teams, team_role_of

EXTERNAL_FIELDS = ("event_title", "event_url", "host", "event_location", "start_datetime", "end_datetime")


class CommunityEventRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		community: DF.Link
		end_datetime: DF.Datetime | None
		event: DF.Link | None
		event_location: DF.Data | None
		event_team: DF.Link | None
		event_title: DF.Data | None
		event_url: DF.Data | None
		google_place_id: DF.Data | None
		host: DF.Data | None
		is_external_event: DF.Check
		latitude: DF.Float
		longitude: DF.Float
		review_note: DF.SmallText | None
		reviewed_by: DF.Link | None
		start_datetime: DF.Datetime | None
		status: DF.Literal["Pending", "Approved", "Rejected"]
		submitted_by: DF.Link | None
	# end: auto-generated types

	def validate(self):
		if self.is_external_event:
			self.validate_external_event()
		else:
			self.validate_buzz_event()
		self.validate_community()

	def validate_buzz_event(self):
		if not self.event:
			frappe.throw(_("Pick the event to list."))
		self.event_title, self.event_team = frappe.db.get_value("Buzz Event", self.event, ["title", "team"])
		# An unpublished event may still be taken off the page.
		if self.status != "Rejected":
			self.validate_event()
		self.validate_unique_pair()

	def validate_external_event(self):
		# The form marks these mandatory, but only the form: the server checks them here.
		labels = [self.meta.get_label(field) for field in EXTERNAL_FIELDS if not self.get(field)]
		if labels:
			frappe.throw(_("An external event needs: {0}").format(", ".join(labels)))
		# Frappe's URL check takes any scheme, and this link renders as an href for curators.
		validate_url(self.event_url, throw=True, valid_schemes=("http", "https"))
		if get_datetime(self.end_datetime) < get_datetime(self.start_datetime):
			frappe.throw(_("The event cannot end before it starts."))
		self.event = self.event_team = None

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
