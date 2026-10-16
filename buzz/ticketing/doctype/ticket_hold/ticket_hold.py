# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Max, Sum
from frappe.utils import add_to_date, now_datetime

HOLD_MINUTES = 10
# How long a paid draft keeps its tickets while the person is on the payment page.
PAYMENT_HOLD_MINUTES = 15


class TicketHold(Document):
	"""Tickets a booking form holds for a short time. A hold counts against capacity while
	`expires_at` is in the future, so expiry needs no job. Release and booking delete it."""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		event: DF.Link
		expires_at: DF.Datetime
		hold_token: DF.Data
		ip_address: DF.Data | None
		quantity: DF.Int
		ticket_type: DF.Link
	# end: auto-generated types


def held_quantities(ticket_types: list, exclude_token: str | None = None, for_update: bool = False) -> dict:
	"""Live held quantity by ticket type name. `for_update` makes it a locking read, as
	`EventTicketType.count_tickets_sold` explains."""
	hold = frappe.qb.DocType("Ticket Hold")
	query = (
		frappe.qb.from_(hold)
		.select(hold.ticket_type, Sum(hold.quantity))
		.where(hold.ticket_type.isin([str(name) for name in ticket_types] or [""]))
		.where(hold.expires_at > now_datetime())
		.groupby(hold.ticket_type)
	)
	if exclude_token:
		query = query.where(hold.hold_token != exclude_token)
	if for_update:
		query = query.for_update()
	return {str(ticket_type): int(quantity) for ticket_type, quantity in query.run()}


def live_hold_expiry(hold_token: str | None):
	"""When the token's live hold ends, or None if it has none."""
	if not hold_token:
		return None
	hold = frappe.qb.DocType("Ticket Hold")
	query = (
		frappe.qb.from_(hold)
		.select(Max(hold.expires_at))
		.where((hold.hold_token == hold_token) & (hold.expires_at > now_datetime()))
	)
	return query.run()[0][0]


def new_hold_expiry():
	return add_to_date(now_datetime(), minutes=HOLD_MINUTES)


def set_hold(hold_token: str, event: str, quantities: dict, expires_at) -> None:
	"""Replace the token's rows with `quantities` (ticket type name to count). The caller
	holds the ticket type locks and has checked capacity."""
	release_hold(hold_token)
	for ticket_type, quantity in quantities.items():
		if quantity <= 0:
			continue
		frappe.get_doc(
			{
				"doctype": "Ticket Hold",
				"hold_token": hold_token,
				"event": event,
				"ticket_type": ticket_type,
				"quantity": quantity,
				"expires_at": expires_at,
				"ip_address": getattr(frappe.local, "request_ip", None),
			}
		).insert(ignore_permissions=True)


def extend_hold(hold_token: str | None, expires_at) -> None:
	if hold_token:
		frappe.db.set_value("Ticket Hold", {"hold_token": hold_token}, "expires_at", expires_at)


def release_hold(hold_token: str | None) -> None:
	if hold_token:
		frappe.db.delete("Ticket Hold", {"hold_token": hold_token})
