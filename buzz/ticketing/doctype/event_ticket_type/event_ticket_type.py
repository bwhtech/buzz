# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

OTHER_CURRENCIES = ("USD",)


def tickets_sold_by_currency(ticket_types: list) -> dict[tuple[str, str], int]:
	from frappe.query_builder.functions import Count

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


class EventTicketType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.ticketing.doctype.event_ticket_type_price.event_ticket_type_price import (
			EventTicketTypePrice,
		)

		auto_unpublish_after: DF.Date | None
		currency: DF.Link
		event: DF.Link
		is_published: DF.Check
		max_tickets_available: DF.Int
		name: DF.Int | None
		price: DF.Currency
		prices: DF.Table[EventTicketTypePrice]
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if not self.is_new() and self.has_value_changed("price") and self.tickets_sold:
			frappe.throw(_("The price of {0} cannot change after tickets are sold").format(self.title))
		self.validate_other_currency_prices()
		self.validate_locked_prices()

	def validate_locked_prices(self):
		before = None if self.is_new() else self.get_doc_before_save()
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

	def validate_other_currency_prices(self):
		currencies = [row.currency for row in self.prices]
		for row in self.prices:
			if row.currency not in OTHER_CURRENCIES or row.currency == self.currency:
				frappe.throw(_("{0} prices are not supported").format(row.currency))
			if currencies.count(row.currency) > 1:
				frappe.throw(_("{0} price is added more than once").format(row.currency))
			if row.price <= 0:
				frappe.throw(_("{0} price must be greater than 0").format(row.currency))

	def price_in(self, currency: str) -> float:
		if currency == self.currency:
			return self.price
		for row in self.prices:
			if row.currency == currency:
				return row.price
		if not self.price:
			return 0
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
