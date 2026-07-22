# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

PROPOSAL_MANAGER_ROLES = frozenset({"System Manager", "Event Manager"})


def is_proposal_manager(user: str) -> bool:
	return user == "Administrator" or bool(PROPOSAL_MANAGER_ROLES & set(frappe.get_roles(user)))


def get_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_proposal_manager(user):
		return ""

	escaped_user = frappe.db.escape(user)
	# Guest form submissions leave owner/submitted_by as "Guest", so speakers
	# are matched by their email in the speakers child table.
	return (
		f"(`tabTalk Proposal`.`submitted_by` = {escaped_user}"
		f" or `tabTalk Proposal`.`owner` = {escaped_user}"
		f" or `tabTalk Proposal`.`name` in ("
		f"select `parent` from `tabProposal Speaker`"
		f" where `parenttype` = 'Talk Proposal' and `email` = {escaped_user}))"
	)


def has_talk_proposal_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	# Controller hooks can only deny access: True means "no objection" and
	# role permissions still apply, False blocks the document outright.
	user = user or frappe.session.user
	if ptype == "create" or doc.is_new():
		return True
	if is_proposal_manager(user):
		return True
	if user in (doc.submitted_by, doc.owner):
		return True
	return any(speaker.email == user for speaker in doc.speakers)


class TalkProposal(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.proposals.doctype.proposal_speaker.proposal_speaker import ProposalSpeaker
		from buzz.ticketing.doctype.additional_field.additional_field import AdditionalField

		additional_fields: DF.Table[AdditionalField]
		description: DF.TextEditor | None
		event: DF.Link
		phone: DF.Phone | None
		speakers: DF.Table[ProposalSpeaker]
		status: DF.Link
		submitted_by: DF.Link | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if not self.submitted_by:
			self.submitted_by = frappe.session.user

	@frappe.whitelist()
	def create_talk(self):
		talk = get_mapped_doc("Talk Proposal", self.name, {"Talk Proposal": {"doctype": "Event Talk"}})

		for speaker in self.speakers:
			user = frappe.db.exists("User", speaker.email)
			if not user:
				user = (
					frappe.get_doc(
						{
							"doctype": "User",
							"first_name": speaker.first_name,
							"last_name": speaker.last_name,
							"email": speaker.email,
						}
					)
					.insert()
					.name
				)

			speaker_profile = frappe.db.exists("Speaker Profile", {"user": user})
			if not speaker_profile:
				speaker_profile = frappe.get_doc({"doctype": "Speaker Profile", "user": user}).insert().name

			talk.append("speakers", {"speaker": speaker_profile})
		return talk.save()
