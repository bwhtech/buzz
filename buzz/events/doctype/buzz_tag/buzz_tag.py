# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buzz.api.tags.services import is_taggable, refresh_user_tags


class BuzzTag(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		document_type: DF.Link
		label: DF.Data
		team: DF.Link
	# end: auto-generated types

	def validate(self):
		self.label = " ".join(self.label.split())
		# Desk keeps a record's tags as one comma-joined string.
		if "," in self.label:
			frappe.throw(_("A tag name cannot contain a comma."))
		if not is_taggable(self.document_type):
			frappe.throw(_("{0} records cannot be tagged.").format(_(self.document_type)))

	def on_update(self):
		if self.has_value_changed("label"):
			refresh_user_tags(self.document_type, self.tagged_names())

	def on_trash(self):
		names = self.tagged_names()
		frappe.db.delete("Buzz Tag Link", {"tag": self.name})
		refresh_user_tags(self.document_type, names)

	def tagged_names(self) -> list[str]:
		return frappe.get_all("Buzz Tag Link", {"tag": self.name}, pluck="document_name")


def on_doctype_update():
	# A label repeats across teams and record types, never within one. The collation ignores case.
	frappe.db.add_unique("Buzz Tag", ["team", "document_type", "label"], constraint_name="unique_tag_label")


def document_team(doctype: str, name: str) -> str | None:
	"""The team a record belongs to, directly or through its event."""
	if frappe.get_meta(doctype).has_field("team"):
		return frappe.db.get_value(doctype, name, "team")
	event = frappe.db.get_value(doctype, name, "event")
	return frappe.db.get_value("Buzz Event", event, "team") if event else None


def delete_tag_links(doc, method=None):
	"""Untag a record as it is deleted, before Frappe checks what still links to it."""
	frappe.db.delete("Buzz Tag Link", {"document_type": doc.doctype, "document_name": doc.name})
