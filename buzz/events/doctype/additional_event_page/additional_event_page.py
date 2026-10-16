# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AdditionalEventPage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		content: DF.TextEditor
		display_order: DF.Int
		event: DF.Link
		is_published: DF.Check
		route: DF.Data | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_duplicate()

	def validate_duplicate(self):
		# The title is the tab's label, so two pages of one event cannot share one.
		if frappe.db.exists(
			"Additional Event Page",
			{"title": self.title, "event": self.event, "name": ["!=", self.name]},
		):
			frappe.throw(
				frappe._("An Additional Event Page with the same title already exists for this event.")
			)
