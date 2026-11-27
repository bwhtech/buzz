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
		self.validate_event_unchanged()
		self.validate_unique_title()

	# Not set_only_once: Buzz Event names are autoincrement ints, and Frappe compares the
	# reloaded int with the saved string, which fails every save.
	def validate_event_unchanged(self):
		before = self.get_doc_before_save()
		if before and str(before.event) != str(self.event):
			frappe.throw(_("A ticket category cannot move to another event"))

	# Runs before Frappe's link check, so the delete goes through with ticket types left uncategorized.
	def on_trash(self):
		frappe.db.set_value("Event Ticket Type", {"category": self.name}, "category", None)

	# The default collation compares titles case-insensitively.
	def validate_unique_title(self):
		filters = {"event": self.event, "title": self.title, "name": ("!=", self.name)}
		if frappe.db.exists("Event Ticket Category", filters):
			frappe.throw(_("A ticket category named {0} already exists for this event").format(self.title))


# Display order: lowest sort_order first, ties by creation.
def get_ordered_categories(event: str | int) -> list[dict]:
	category = frappe.qb.DocType("Event Ticket Category")
	return (
		frappe.qb.from_(category)
		.select(category.name, category.title, category.description, category.sort_order)
		.where(category.event == str(event))
		.orderby(category.sort_order)
		.orderby(category.creation)
	).run(as_dict=True)


def on_doctype_update():
	frappe.db.add_index("Event Ticket Category", ["event", "sort_order"])


# Creates an event's categories from template rows. Maps each title to the new category's name.
def create_ticket_categories(event: str, rows) -> dict[str, str]:
	names = {}
	for row in rows:
		category = frappe.get_doc(
			{
				"doctype": "Event Ticket Category",
				"event": event,
				"title": row.title,
				"description": row.description,
				"sort_order": row.sort_order,
			}
		).insert()
		names[category.title] = category.name
	return names
