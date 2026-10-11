# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EventPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		currency: DF.Link | None
		name: DF.Int | None
		order_id: DF.Data | None
		payment_gateway: DF.Link | None
		payment_request: DF.Link | None
		payment_id: DF.Data | None
		payment_received: DF.Check
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		user: DF.Link
	# end: auto-generated types

	pass
