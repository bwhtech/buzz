# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BuzzCustomField(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		applied_to: DF.Literal["Booking", "Ticket", "Offline Payment Form"]
		default_value: DF.Data | None
		enabled: DF.Check
		event: DF.Link
		fieldname: DF.Data | None
		fieldtype: DF.Literal[
			"Data", "Check", "Small Text", "Phone", "Email", "Select", "Date", "Number", "Multi Select"
		]
		label: DF.Data
		mandatory: DF.Check
		options: DF.SmallText | None
		order: DF.Int
		placeholder: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if (
			self.enabled
			and self.applied_to == "Custom Form"
			and self.custom_form_doctype == "Sponsorship Enquiry"
		):
			frappe.throw(_("Add sponsorship questions to Sponsor Enquiry Form."))
		if not self.fieldname:
			self.fieldname = frappe.scrub(self.label)

	def on_update(self):
		if self.applied_to == "Custom Form" and self.custom_form_doctype:
			self.create_additional_fields_if_missing()

	def create_additional_fields_if_missing(self):
		meta = frappe.get_meta(self.custom_form_doctype)

		if meta.has_field("additional_fields"):
			return

		frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": self.custom_form_doctype,
				"fieldname": "section_break_additional",
				"label": "Additional Fields",
				"fieldtype": "Section Break",
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": self.custom_form_doctype,
				"fieldname": "additional_fields",
				"label": "Additional Fields",
				"fieldtype": "Table",
				"options": "Additional Field",
				"insert_after": "section_break_additional",
			}
		).insert(ignore_permissions=True)

		frappe.msgprint(
			_("Added 'Additional Fields' table to {0}").format(self.custom_form_doctype),
			alert=True,
		)
