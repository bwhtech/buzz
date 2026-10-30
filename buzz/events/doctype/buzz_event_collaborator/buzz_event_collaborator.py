# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.core.doctype.user_invitation.user_invitation import INVITATION_EXPIRY_DAYS
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, get_url, now_datetime, sha256_hash

from buzz.events.doctype.buzz_team_membership.buzz_team_membership import sync_frappe_roles
from buzz.permissions import SECTIONS

INVITE_PAGE_PATH = "/b/manage/collaborator-invite"


class BuzzEventCollaborator(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		communications_access: DF.Literal["", "View", "Edit"]
		details_access: DF.Literal["View", "Edit"]
		email: DF.Data
		event: DF.Link
		guests_access: DF.Literal["", "View", "Edit"]
		invite_key_hash: DF.Data | None
		invited_at: DF.Datetime | None
		invited_by: DF.Link | None
		sponsors_access: DF.Literal["", "View", "Edit"]
		status: DF.Literal["Pending", "Accepted", "Revoked"]
		talks_access: DF.Literal["", "View", "Edit"]
		team: DF.Link | None
		ticketing_access: DF.Literal["", "View", "Edit"]
		user: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.email = self.email.strip().lower()
		self.validate_duplicate()
		self.validate_has_a_section()

	def validate_duplicate(self):
		existing = frappe.db.exists(
			"Buzz Event Collaborator",
			{"event": self.event, "email": self.email, "name": ("!=", self.name)},
		)
		if existing:
			frappe.throw(_("{0} is already invited to this event.").format(self.email))

	def validate_has_a_section(self):
		# Details View alone opens no page in the dashboard.
		if self.details_access != "Edit" and not any(
			self.get(f"{section}_access") for section in SECTIONS[1:]
		):
			frappe.throw(_("Give {0} access to at least one section.").format(self.email))

	def on_update(self):
		self.sync_roles()

	def after_delete(self):
		self.sync_roles()

	def sync_roles(self):
		if self.user:
			sync_frappe_roles(self.user)

	@property
	def is_expired(self) -> bool:
		return get_datetime(self.invited_at) < add_days(now_datetime(), -INVITATION_EXPIRY_DAYS)

	def granted_sections(self) -> list[str]:
		return [
			f"{section.title()}: {self.get(f'{section}_access')}"
			for section in SECTIONS
			if self.get(f"{section}_access")
		]

	def issue_invitation(self, invited_by: str) -> None:
		"""Mail a fresh key; an earlier one stops working."""
		key = frappe.generate_hash()
		self.update(
			{
				"status": "Pending",
				"invite_key_hash": sha256_hash(key),
				"invited_by": invited_by,
				"invited_at": now_datetime(),
			}
		)
		self.save(ignore_permissions=True)
		self.send_invitation_mail(key)

	def send_invitation_mail(self, key: str) -> None:
		event_title = frappe.db.get_value("Buzz Event", self.event, "title")
		frappe.sendmail(
			recipients=[self.email],
			subject=_("You have been invited to collaborate on {0}").format(event_title),
			template="event_collaborator_invitation",
			raw_html=True,
			add_css=False,
			args={
				"inviter": frappe.utils.get_fullname(self.invited_by),
				"event_title": event_title,
				"sections": self.granted_sections(),
				"invite_link": get_url(f"{INVITE_PAGE_PATH}?key={key}"),
				"expiry_days": INVITATION_EXPIRY_DAYS,
			},
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

	def accept(self, user: str) -> None:
		self.update({"status": "Accepted", "user": user, "invite_key_hash": None})
		self.save(ignore_permissions=True)

	def revoke(self) -> None:
		self.update({"status": "Revoked", "invite_key_hash": None})
		self.save(ignore_permissions=True)
