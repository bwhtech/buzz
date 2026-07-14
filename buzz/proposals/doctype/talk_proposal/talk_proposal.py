# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


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
