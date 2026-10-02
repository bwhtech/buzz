# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Count

from buzz.events.doctype.buzz_price.buzz_price import validate_unique_currencies


def tickets_sold_by_currency(ticket_types: list) -> dict[tuple[str, str], int]:
	booking = frappe.qb.DocType("Event Booking")
	attendee = frappe.qb.DocType("Event Booking Attendee")
	rows = (
		frappe.qb.from_(attendee)
		.join(booking)
		.on(booking.name == attendee.parent)
		.select(attendee.ticket_type, attendee.currency, Count(attendee.name))
		.where((booking.docstatus == 1) & attendee.ticket_type.isin(ticket_types or [""]))
		.groupby(attendee.ticket_type, attendee.currency)
	).run()
	return {(str(ticket_type), currency): count for ticket_type, currency, count in rows}


def default_currency(event: str) -> str:
	"""Default currency of the ticket type the booking page lists first; fixed coupon amounts are in it."""
	filters = {"event": event, "is_published": 1}
	ticket_type = frappe.db.get_value("Event Ticket Type", filters, "name", order_by="creation desc")
	price = {"parenttype": "Event Ticket Type", "parent": str(ticket_type), "idx": 1}
	return frappe.db.get_value("Buzz Price", price, "currency") or "INR"


class EventTicketType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.buzz_price.buzz_price import BuzzPrice

		auto_unpublish_after: DF.Date | None
		event: DF.Link
		is_published: DF.Check
		max_tickets_available: DF.Int
		name: DF.Int | None
		prices: DF.Table[BuzzPrice]
		title: DF.Data
	# end: auto-generated types

	def before_validate(self):
		if not self.prices:
			self.append("prices", {"currency": "INR", "price": 0})

	def validate(self):
		validate_unique_currencies(self.prices)
		self.validate_paid_in_every_currency()
		self.validate_locked_prices()

	@property
	def is_free(self) -> bool:
		return not self.prices[0].price

	def validate_paid_in_every_currency(self):
		if not self.is_free and not all(row.price for row in self.prices):
			frappe.throw(_("{0} needs a price above 0 in every currency").format(self.title))

	def validate_locked_prices(self):
		before = self.get_doc_before_save()
		if not before:
			return
		current = {row.currency: row.price for row in self.prices}
		sold = tickets_sold_by_currency([self.name])
		for row in before.prices:
			if sold.get((str(self.name), row.currency)) and current.get(row.currency) != row.price:
				frappe.throw(
					_("The {0} price of {1} cannot change after {0} tickets are sold").format(
						row.currency, self.title
					)
				)

	def price_in(self, currency: str) -> float:
		if self.is_free:
			return 0
		for row in self.prices:
			if row.currency == currency:
				return row.price
		frappe.throw(_("{0} tickets can't be paid in {1}").format(self.title, currency))

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
