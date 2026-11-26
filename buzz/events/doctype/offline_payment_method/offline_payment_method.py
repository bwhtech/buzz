# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class OfflinePaymentMethod(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		collect_payment_proof: DF.Check
		description: DF.TextEditor | None
		enabled: DF.Check
		event: DF.Link
		name: DF.Int | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_unique_title()

	def validate_unique_title(self):
		existing = frappe.db.exists(
			"Offline Payment Method",
			{"title": self.title, "event": self.event, "name": ("!=", self.name)},
		)
		if existing:
			frappe.throw(
				_("An offline payment method with title {0} already exists for this event").format(
					frappe.bold(self.title)
				)
			)


def on_doctype_update():
	frappe.db.add_index("Offline Payment Method", ["event", "enabled"])
