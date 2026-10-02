# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def validate_unique_currencies(prices: list) -> None:
	currencies = [row.currency for row in prices]
	if len(currencies) != len(set(currencies)):
		frappe.throw(_("Each currency can have only one price."))


class BuzzPrice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		price: DF.Currency
	# end: auto-generated types

	pass
