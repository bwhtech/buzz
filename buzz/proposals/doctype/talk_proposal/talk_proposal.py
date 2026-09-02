# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Criterion
from frappe.utils import cstr, getdate

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


PENDING = "Review Pending"
WITHDRAWN = "Withdrawn"


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

	@property
	def speaker_emails(self) -> set[str]:
		return {speaker.email.lower() for speaker in self.speakers if speaker.email}

	@property
	def is_closed(self) -> bool:
		if self.status != PENDING:
			return True

		dates = frappe.db.get_value("Buzz Event", self.event, ["start_date", "end_date"], as_dict=True)
		if not dates:
			return True

		# A run that ends today is not over yet, so end_date decides.
		last = dates.end_date or dates.start_date
		return bool(last) and last < getdate()

	def validate(self):
		self.validate_event_is_unchanged()

		if not self.submitted_by:
			self.submitted_by = frappe.session.user

		self.restrict_speaker_changes()

	def validate_event_is_unchanged(self):
		"""A proposal stays with the event it was submitted to, whoever is saving it."""
		before = self.get_doc_before_save()
		if not before or not before.event:
			return

		# cstr: an autoincrement name is an int in memory and a string out of the database.
		if cstr(self.event) != cstr(before.event):
			frappe.throw(
				_("A proposal cannot be moved to another event. Submit a new one there instead."),
				frappe.CannotChangeConstantError,
			)

	def restrict_speaker_changes(self):
		"""The drawer's rules, on the server: a speaker holds plain write on the document."""
		before = self.get_doc_before_save()
		user = frappe.session.user
		if not before or not is_speaker_on(before, user):
			return
		# Safe on the incoming document only because validate_event_is_unchanged has already
		# refused any change to `event`, which is what decides the team here.
		if derived_has_permission(self, ptype="write", user=user):
			return

		if before.is_closed:
			frappe.throw(_("This proposal can no longer be changed."), frappe.PermissionError)

		if self.status not in (before.status, WITHDRAWN):
			frappe.throw(_("A proposal can only be withdrawn."), frappe.PermissionError)

		if self.submitted_by != before.submitted_by:
			frappe.throw(_("A proposal stays with its submitter."), frappe.PermissionError)

		# Dropping your own row would take away your access to the proposal.
		if user.lower() in before.speaker_emails and user.lower() not in self.speaker_emails:
			frappe.throw(_("You cannot remove yourself from a proposal."), frappe.PermissionError)

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
