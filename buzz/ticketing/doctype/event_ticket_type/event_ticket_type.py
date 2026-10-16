# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Count

from buzz.events.doctype.buzz_price.buzz_price import validate_unique_currencies
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import is_feature_enabled
from buzz.ticketing.doctype.ticket_hold.ticket_hold import held_quantities

PAID_EVENTS_FLAG = "feature_paid_events"


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
		category: DF.Link | None
		description: DF.SmallText | None
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
		self.validate_free_or_paid_everywhere()
		self.validate_locked_prices()
		self.validate_paid_events_enabled()
		self.validate_category_event()

	def validate_category_event(self):
		filters = {"name": self.category, "event": self.event}
		if self.category and not frappe.db.exists("Event Ticket Category", filters):
			frappe.throw(_("The ticket category of {0} belongs to another event").format(self.title))

	@property
	def is_free(self) -> bool:
		return not self.prices[0].price

	# A ticket free in its default currency is free everywhere (see price_in), so a mix of
	# free and paid rows would quietly give the paid currency away.
	def validate_free_or_paid_everywhere(self):
		paid = [bool(row.price) for row in self.prices]
		if any(paid) and not all(paid):
			frappe.throw(_("{0} must be free in every currency or paid in every currency").format(self.title))

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

	# Only a ticket turning paid is checked, so a team without the flag can still edit or
	# disable the paid ticket types it already has.
	def validate_paid_events_enabled(self):
		before = self.get_doc_before_save()
		if self.is_free or (before and not before.is_free):
			return
		team = frappe.get_cached_value("Buzz Event", self.event, "team")
		if not is_feature_enabled(team, PAID_EVENTS_FLAG):
			frappe.throw(_("Paid tickets are not enabled for this team. Contact your administrator."))

	def price_in(self, currency: str) -> float:
		if self.is_free:
			return 0
		for row in self.prices:
			if row.currency == currency:
				return row.price
		frappe.throw(_("{0} tickets can't be paid in {1}").format(self.title, currency))

	def are_tickets_available(self, num_tickets: int, hold_token: str | None = None) -> bool:
		remaining = self.get_remaining_tickets(hold_token=hold_token)
		return remaining == -1 or remaining >= num_tickets

	@property
	def tickets_sold(self) -> int:
		"""Returns the number of tickets sold for this ticket type."""
		return self.count_tickets_sold()

	@property
	def remaining_tickets(self) -> int:
		"""Returns -1 if no limit, otherwise the number of remaining tickets."""
		return self.get_remaining_tickets()

	def get_remaining_tickets(self, for_update: bool = False, hold_token: str | None = None) -> int:
		"""Tickets neither sold nor held by anyone but `hold_token`, or -1 if no limit."""
		if not self.max_tickets_available:
			return -1
		held = held_quantities([self.name], hold_token, for_update).get(str(self.name), 0)
		return self.max_tickets_available - self.count_tickets_sold(for_update) - held

	def count_tickets_sold(self, for_update: bool = False) -> int:
		"""With `for_update`, a locking read: under REPEATABLE READ a plain count reads the
		transaction's snapshot and misses tickets another booking committed after it."""
		ticket = frappe.qb.DocType("Event Ticket")
		query = (
			frappe.qb.from_(ticket)
			.select(Count(ticket.name))
			.where((ticket.ticket_type == self.name) & (ticket.docstatus == 1))
		)
		if for_update:
			query = query.for_update()
		return query.run()[0][0]


def start_capacity_transaction() -> None:
	"""Start a READ COMMITTED transaction for a write that changes ticket availability.

	Under REPEATABLE READ with `innodb_snapshot_isolation` (on by default since MariaDB 11.6),
	a row another booking changed after this transaction's first read can't be locked: the
	naming series alone fails every concurrent booking but one with "Record has changed since
	last read". READ COMMITTED reads the latest committed rows once the lock is held.
	"""
	frappe.db.sql("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
	frappe.db.commit()  # nosemgrep: frappe-manual-commit


def lock_ticket_types(names: list) -> None:
	"""Lock the ticket type rows, in name order so two bookings can't deadlock, until the
	transaction ends. Bookings of the same ticket type then check capacity one at a time."""
	if not names:
		return
	ticket_type = frappe.qb.DocType("Event Ticket Type")
	(
		frappe.qb.from_(ticket_type)
		.select(ticket_type.name)
		.where(ticket_type.name.isin(names))
		.orderby(ticket_type.name)
		.for_update()
	).run()
