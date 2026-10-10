# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buzz.events.doctype.buzz_tag.buzz_tag import document_team


class BuzzTagLink(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		document_name: DF.DynamicLink
		document_type: DF.Link
		tag: DF.Link
	# end: auto-generated types

	def validate(self):
		tag = frappe.db.get_value("Buzz Tag", self.tag, ["team", "document_type"], as_dict=True)
		record_team = document_team(self.document_type, self.document_name)
		if tag.document_type != self.document_type or tag.team != record_team:
			frappe.throw(_("This tag belongs to another team or kind of record."))


def on_doctype_update():
	frappe.db.add_unique(
		"Buzz Tag Link", ["tag", "document_type", "document_name"], constraint_name="unique_tag_link"
	)
	frappe.db.add_index("Buzz Tag Link", ["document_type", "document_name"])
