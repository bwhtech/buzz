# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class SponsorshipTier(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		enabled: DF.Check
		event: DF.Link
		perks: DF.SmallText | None
		price: DF.Currency
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_event_is_unchanged()

	def validate_event_is_unchanged(self):
		before = self.get_doc_before_save()
		if before and cstr(before.event) != cstr(self.event):
			frappe.throw(
				_("A sponsorship tier cannot be moved to another event."), frappe.CannotChangeConstantError
			)
