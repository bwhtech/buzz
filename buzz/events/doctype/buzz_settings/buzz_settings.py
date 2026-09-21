# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BuzzSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accept_event_proposals: DF.Check
		allow_add_ons_change_before_event_start_days: DF.Int
		allow_guest_event_proposals: DF.Check
		allow_ticket_cancellation_request_before_event_start_days: DF.Int
		allow_transfer_ticket_before_event_start_days: DF.Int
		auto_send_pitch_deck: DF.Check
		default_sponsor_deck_cc: DF.SmallText | None
		default_sponsor_deck_email_template: DF.Link | None
		default_sponsor_deck_reply_to: DF.Data | None
		default_ticket_email_template: DF.Link | None
		event_page_theme: DF.Literal["classic", "paper"]
		event_proposal_banner_title: DF.Data | None
		event_proposal_success_message: DF.MarkdownEditor | None
		event_proposal_success_title: DF.Data | None
		login_banner: DF.MarkdownEditor | None
		support_email: DF.Data | None
	# end: auto-generated types

	def validate(self):
		"""Validate the settings."""
		self.validate_transfer_days()

	def validate_transfer_days(self):
		"""Validate that transfer days is a reasonable value."""
		if self.allow_transfer_ticket_before_event_start_days is not None:
			if self.allow_transfer_ticket_before_event_start_days < 0:
				frappe.throw(_("Allow Transfer Ticket Before Event Start Days cannot be negative."))
			elif self.allow_transfer_ticket_before_event_start_days > 365:
				frappe.throw(_("Allow Transfer Ticket Before Event Start Days cannot be more than 365 days."))
