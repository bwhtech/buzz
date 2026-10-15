# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EventTemplateTicketType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_unpublish_after: DF.Date | None
		category: DF.Data | None
		currency: DF.Link
		is_published: DF.Check
		max_tickets_available: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		price: DF.Currency
		title: DF.Data
	# end: auto-generated types

	pass
