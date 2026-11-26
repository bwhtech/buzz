# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EventBookingAttendee(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		add_on_total: DF.Currency
		add_ons: DF.Link | None
		amount: DF.Currency
		currency: DF.Link
		custom_fields: DF.JSON | None
		email: DF.Data
		first_name: DF.Data
		full_name: DF.Data
		last_name: DF.Data | None
		number_of_add_ons: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		ticket_type: DF.Link
	# end: auto-generated types

	def before_validate(self):
		# Backward compat: split full_name into first/last if first_name not provided
		if not self.first_name and self.full_name:
			name_parts = self.full_name.strip().split(" ", 1)
			self.first_name = name_parts[0]
			if not self.last_name and len(name_parts) > 1:
				self.last_name = name_parts[1]

	def before_save(self):
		self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()

	def get_add_on_total(self):
		if not self.add_ons:
			return 0
		doc = frappe.get_cached_doc("Attendee Ticket Add-on", self.add_ons)
		add_ons = doc.add_ons
		return sum(r.price for r in add_ons)

	def get_number_of_add_ons(self):
		return len(frappe.get_cached_doc("Attendee Ticket Add-on", self.add_ons).add_ons)


def on_doctype_update():
	frappe.db.add_index("Event Booking Attendee", ["ticket_type", "parent"])
	frappe.db.add_index("Event Booking Attendee", ["parent", "ticket_type", "currency"])
