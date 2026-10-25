# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buzz.ticketing.approval import validate_free_only


class TicketAddon(Document):
	def validate(self):
		self.validate_duplicate_title()
		validate_free_only(self.event, False, bool(self.price))

	def validate_duplicate_title(self):
		if frappe.db.exists(
			self.doctype,
			{
				"event": self.event,
				"title": self.title,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("Add-on <b>{0}</b> already exists for this event").format(self.title))
