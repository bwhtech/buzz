# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EventTemplateCustomField(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		default_value: DF.Data | None
		depends_on: DF.JSON | None
		description: DF.SmallText | None
		enabled: DF.Check
		fieldname: DF.Data | None
		fieldtype: DF.Literal[
			"Data",
			"Check",
			"Small Text",
			"Phone",
			"Email",
			"Select",
			"Date",
			"Number",
			"Multi Select",
			"Rating",
			"Attach",
			"Attach Image",
			"URL",
			"Radio",
			"Heading",
			"Paragraph",
			"Divider",
			"Page Break",
		]
		form_doctype: DF.Link
		label: DF.Data
		mandatory: DF.Check
		mandatory_depends_on: DF.JSON | None
		options: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		placeholder: DF.Data | None
		width: DF.Literal["Full", "Half"]
	# end: auto-generated types

	pass
