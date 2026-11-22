# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HostedPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		currency: DF.Link
		customer_email: DF.Data | None
		customer_phone: DF.Data | None
		payment_method: DF.Data | None
		payment_request: DF.Link | None
		reference: DF.Data | None
		refunded_amount: DF.Currency
		return_url: DF.SmallText
		status: DF.Literal[
			"Pending", "Paid", "Not Paid", "Cancelled", "Expired", "Partially Refunded", "Refunded"
		]
		team: DF.Link
		webhook_url: DF.SmallText
	# end: auto-generated types

	def on_payment_authorized(self, status: str) -> None:
		payment_method = frappe.db.get_value(
			"Gateway Payment Request", self.payment_request, "payment_method"
		)
		self.db_set({"status": "Paid", "payment_method": payment_method})
