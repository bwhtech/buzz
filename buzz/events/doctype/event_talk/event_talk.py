# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EventTalk(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.talk_speaker.talk_speaker import TalkSpeaker

		description: DF.TextEditor | None
		event: DF.Link
		name: DF.Int | None
		proposal: DF.Link | None
		speakers: DF.Table[TalkSpeaker]
		submitted_by: DF.Link
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if frappe.db.exists("Event Talk", {"proposal": self.proposal, "name": ["!=", self.name]}):
			frappe.throw(_("Talk already created for this proposal!"))
