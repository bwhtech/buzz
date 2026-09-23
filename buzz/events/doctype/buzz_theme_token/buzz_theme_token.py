# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BuzzThemeToken(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dark_value: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		token: DF.Data
		type: DF.Literal["Color", "Dimension", "Font"]
		value: DF.Data
	# end: auto-generated types
