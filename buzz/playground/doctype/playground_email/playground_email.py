# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PlaygroundEmail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		message: DF.LongText | None
		recipient: DF.Data | None
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		sandbox: DF.Link | None
		sender: DF.Data | None
		subject: DF.SmallText | None
	# end: auto-generated types
	pass
