# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Criterion

from buzz.permissions import derived_has_permission, derived_query_conditions


def get_speaker_query_conditions(user: str) -> Criterion:
	proposal = frappe.qb.DocType("Talk Proposal")
	speaker = frappe.qb.DocType("Proposal Speaker")
	# Guest form submissions leave owner/submitted_by as "Guest", so speakers
	# are matched by their email in the speakers child table.
	speaker_rows = (
		frappe.qb.from_(speaker)
		.select(speaker.parent)
		.where((speaker.parenttype == "Talk Proposal") & (speaker.email == user))
	)
	return (proposal.submitted_by == user) | (proposal.owner == user) | proposal.name.isin(speaker_rows)


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> Criterion | None:
	user = user or frappe.session.user
	team_conditions = derived_query_conditions(user=user, doctype="Talk Proposal")
	if team_conditions is None:
		return None

	return get_speaker_query_conditions(user) | team_conditions


def is_speaker_on(doc, user: str) -> bool:
	if user in (doc.submitted_by, doc.owner):
		return True
	# User emails are stored lowercase, but guest-entered speaker emails keep
	# their original casing.
	return any(speaker.email and speaker.email.lower() == user.lower() for speaker in doc.speakers)


def has_talk_proposal_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	# Controller hooks can only deny access: True means "no objection" and
	# role permissions still apply, False blocks the document outright.
	user = user or frappe.session.user
	if ptype == "create" or doc.is_new():
		return True
	if is_speaker_on(doc, user):
		return True
	return derived_has_permission(doc, ptype=ptype, user=user)


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
		# A listed speaker holds write on their own proposal, so has_permission("write")
		# would wave them through their own acceptance. Accepting belongs to the event's
		# team, which is what the derived rule asks on its own. That rule waves through a
		# team-less document, which cannot happen here: Buzz Event.team is mandatory.
		if not derived_has_permission(self, ptype="write"):
			frappe.throw(_("Only the event's team can accept a proposal."), frappe.PermissionError)

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
							"user_type": "Website User",
						}
					)
					.insert()
					.name
				)

			speaker_profile = frappe.db.exists("Speaker Profile", {"user": user})
			if not speaker_profile:
				speaker_profile = frappe.get_doc({"doctype": "Speaker Profile", "user": user}).insert().name

			talk.append("speakers", {"speaker": speaker_profile})

		talk.save()
		self.status = "Accepted"
		self.save()
		return talk
