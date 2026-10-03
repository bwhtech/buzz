import frappe
from frappe.query_builder.functions import Count
from frappe.utils import flt

from buzz.api.booking.services import are_registrations_closed
from buzz.api.events.schemas import (
	EventTicketTypes,
	PaymentProviderItem,
	TicketTypeItem,
	TicketTypePrice,
)
from buzz.api.events.services import ensure_event_team_access, registration_link
from buzz.api.events.taxes import team_tax_details
from buzz.payments import get_payment_gateways_for_event
from buzz.permissions import can_manage_members, has_team_access
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
		apply_tax=bool(doc.apply_tax),
		tax_inclusive=bool(doc.tax_inclusive),
		# Same defaults as Buzz Event's validate_tax_settings, so the form opens filled in.
		tax_label=doc.tax_label or "GST",
		tax_percentage=flt(doc.tax_percentage) or 18,
		**team_tax_details(doc.team),
		can_edit_team=can_manage_members(doc.team),
		ticket_types=[ticket_type_item(row, sold, sold_by_currency) for row in rows],
		payment_providers=payment_providers(event),
	)


def payment_providers(event: str) -> list[PaymentProviderItem]:
	default = frappe.db.get_single_value("Buzz Settings", "default_payment_gateway")
	return [
		PaymentProviderItem(name=gateway, is_default=gateway == default)
		for gateway in get_payment_gateways_for_event(event)
	]


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
