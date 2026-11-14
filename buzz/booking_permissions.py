# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

"""Row scoping for records that reach their event through a booking, and for speaker profiles."""

import frappe
from frappe.query_builder import Criterion
from frappe.query_builder.builder import QueryBuilder

from buzz.permissions import (
	WRITE_PTYPES,
	as_sql,
	events_with_section_access,
	events_with_transactions_access,
	has_section_permission,
	is_unrestricted,
	transactions_allows,
)

# Money records follow the transactions rule; the rest of a booking follows the guests section.
TRANSACTION_DOCTYPES = frozenset({"Event Payment", "Event Booking Refund"})


def bookings_of_events(events: QueryBuilder) -> QueryBuilder:
	booking = frappe.qb.DocType("Event Booking")
	return frappe.qb.from_(booking).select(booking.name).where(booking.event.isin(events))


def readable_bookings(user: str, doctype: str) -> QueryBuilder:
	if doctype in TRANSACTION_DOCTYPES:
		return bookings_of_events(events_with_transactions_access(user))
	return bookings_of_events(events_with_section_access(user, "guests"))


def booking_criterion(user: str, doctype: str) -> Criterion:
	table = frappe.qb.DocType(doctype)
	bookings = readable_bookings(user, doctype)
	if doctype == "Event Payment":
		return (table.reference_doctype == "Event Booking") & table.reference_docname.isin(bookings)
	if doctype == "Attendee Ticket Add-on":
		attendee = frappe.qb.DocType("Event Booking Attendee")
		return table.name.isin(
			frappe.qb.from_(attendee).select(attendee.add_ons).where(attendee.parent.isin(bookings))
		)
	return table.booking.isin(bookings)


def booking_query_conditions(user: str | None = None, doctype: str | None = None, **kwargs) -> str | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None
	return as_sql(booking_criterion(user, doctype))


def booking_of(doc) -> str | None:
	if doc.doctype == "Event Payment":
		return doc.reference_docname if doc.reference_doctype == "Event Booking" else None
	if doc.doctype == "Attendee Ticket Add-on":
		return frappe.db.get_value("Event Booking Attendee", {"add_ons": doc.name}, "parent")
	return doc.booking


def booking_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	"""Access on the booking's event. Booking flows insert these past permissions."""
	user = user or frappe.session.user
	if is_unrestricted(user):
		return True

	booking = booking_of(doc)
	event = frappe.db.get_value("Event Booking", booking, "event") if booking else None
	if not event:
		return False
	if doc.doctype in TRANSACTION_DOCTYPES:
		return transactions_allows(event, ptype, user)
	return has_section_permission(event, "guests", ptype, user)


def speaker_profile_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	"""Profiles are public bios: anyone with the role reads or creates one, only its speaker edits it."""
	user = user or frappe.session.user
	if ptype not in WRITE_PTYPES or ptype == "create" or is_unrestricted(user):
		return True
	return user in (doc.user, doc.owner)


def ensure_guests_access(event: str | None) -> None:
	"""Reports read guest data with the query builder, so they check the event themselves."""
	if event and not has_section_permission(event, "guests", "read", frappe.session.user):
		raise frappe.PermissionError


def guest_section_events() -> list[str]:
	user = frappe.session.user
	if is_unrestricted(user):
		return frappe.get_all("Buzz Event", pluck="name")
	return events_with_section_access(user, "guests").run(pluck=True)
