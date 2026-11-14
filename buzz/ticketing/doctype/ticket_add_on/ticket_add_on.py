# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def add_on_options(options: str | None) -> list[str]:
	return options.split("\n") if options else []


class TicketAddon(Document):
	def validate(self):
		self.validate_duplicate_title()
		self.validate_ticket_types()

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

	def validate_ticket_types(self):
		types = {str(row.ticket_type) for row in self.ticket_types}
		if types and frappe.db.count(
			"Event Ticket Type", {"name": ["in", list(types)], "event": self.event}
		) != len(types):
			frappe.throw(_("An add-on can only apply to ticket types of its own event."))
