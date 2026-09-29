# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EventCheckIn(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		date: DF.Date | None
		event: DF.Link
		ticket: DF.Link
	# end: auto-generated types

	def before_insert(self):
		if not self.date:
			self.date = frappe.utils.today()
