# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EventTicketCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		event: DF.Link
		sort_order: DF.Int
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.title = (self.title or "").strip()
		self.validate_unique_title()

	# The default collation compares titles case-insensitively.
	def validate_unique_title(self):
		filters = {"event": self.event, "title": self.title, "name": ("!=", self.name)}
		if frappe.db.exists("Event Ticket Category", filters):
			frappe.throw(_("A ticket category named {0} already exists for this event").format(self.title))
