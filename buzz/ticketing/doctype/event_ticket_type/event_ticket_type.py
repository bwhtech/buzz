# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EventTicketType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_unpublish_after: DF.Date | None
		currency: DF.Link
		event: DF.Link
		is_published: DF.Check
		max_tickets_available: DF.Int
		name: DF.Int | None
		price: DF.Currency
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if not self.is_new() and self.has_value_changed("price") and self.tickets_sold:
			frappe.throw(_("The price of {0} cannot change after tickets are sold").format(self.title))

	def are_tickets_available(self, num_tickets: int) -> bool:
		if self.remaining_tickets != -1 and self.remaining_tickets < num_tickets:
			return False
		return True

	@property
	def tickets_sold(self) -> int:
		"""Returns the number of tickets sold for this ticket type."""
		return frappe.db.count("Event Ticket", {"ticket_type": self.name, "docstatus": 1})

	@property
	def remaining_tickets(self) -> int:
		"""Returns -1 if no limit, otherwise the number of remaining tickets."""
		if not self.max_tickets_available:
			return -1
		return self.max_tickets_available - self.tickets_sold
