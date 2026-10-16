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
		self.validate_route()
		self.validate_duplicate()

	def validate_route(self):
		# The title is the only name an author writes; the slug follows it, so a rename
		# moves the public URL rather than leaving the page on a title it no longer has.
		# The field stays read_only, and Desk shows the result.
		self.route = frappe.website.utils.cleanup_page_name(self.title).replace("_", "-")
		if not self.route:
			frappe.throw(frappe._("Give the page a title with letters or numbers."))

	def validate_duplicate(self):
		if not self.route:
			return

		if frappe.db.exists(
			"Additional Event Page",
			{"route": self.route, "event": self.event, "name": ["!=", self.name]},
		):
			frappe.throw(
				frappe._("An Additional Event Page with the same route already exists for this event.")
			)
