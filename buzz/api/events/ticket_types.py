import frappe
from frappe.query_builder.functions import Count

from buzz.api.booking.services import are_registrations_closed
from buzz.api.events.schemas import EventTicketTypes, TicketTypeItem, TicketTypePrice
from buzz.api.events.services import ensure_event_team_access, registration_link
from buzz.permissions import has_team_access
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import tickets_sold_by_currency

TICKET_TYPE_FIELDS = [
	"name",
	"title",
	"max_tickets_available",
	"auto_unpublish_after",
	"is_published",
	{"prices": ["currency", "price"]},
]


def event_ticket_types(event: str) -> EventTicketTypes:
	ensure_event_team_access(event)
	doc = frappe.get_cached_doc("Buzz Event", event)
	rows = frappe.get_all(
		"Event Ticket Type",
		filters={"event": event},
		fields=TICKET_TYPE_FIELDS,
		order_by="creation asc",
		ignore_permissions=True,
	)
	sold = tickets_sold_by_type(event)
	sold_by_currency = tickets_sold_by_currency([row.name for row in rows])
	return EventTicketTypes(
		title=doc.title,
		can_write=has_team_access(doc.team, "write", frappe.session.user),
		registration_link=registration_link(doc),
		registrations_closed=are_registrations_closed(doc),
		allow_guest_booking=bool(doc.allow_guest_booking),
		guest_verification_method=doc.guest_verification_method or "None",
		ticket_types=[ticket_type_item(row, sold, sold_by_currency) for row in rows],
	)


def ticket_type_item(row, sold: dict, sold_by_currency: dict) -> TicketTypeItem:
	name = str(row.name)
	prices = [
		TicketTypePrice(**price, tickets_sold=sold_by_currency.get((name, price.currency), 0))
		for price in row.prices
	]
	return TicketTypeItem(**{**row, "name": name, "tickets_sold": sold.get(name, 0), "prices": prices})


def tickets_sold_by_type(event: str) -> dict[str, int]:
	ticket = frappe.qb.DocType("Event Ticket")
	rows = (
		frappe.qb.from_(ticket)
		.select(ticket.ticket_type, Count(ticket.name))
		.where((ticket.event == event) & (ticket.docstatus == 1))
		.groupby(ticket.ticket_type)
	).run()
	return {str(ticket_type): count for ticket_type, count in rows}
