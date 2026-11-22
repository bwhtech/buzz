# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class HostedPaymentRate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_method: DF.Data
		rate: DF.Percent
	# end: auto-generated types

	pass
