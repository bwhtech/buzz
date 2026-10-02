import frappe
from frappe.query_builder.functions import Count

from buzz.api.events.exceptions import CannotManageEvent, TicketTypeHasSales, TicketTypeNotFound
from buzz.api.events.schemas import EventTicketTypes, TicketTypeInput, TicketTypeItem, TicketTypePrice
from buzz.api.events.services import ensure_event_team_access
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


class TicketTypesEditor:
	def __init__(self, event: str):
		ensure_event_team_access(event)
		team = frappe.db.get_value("Buzz Event", event, "team")
		if not has_team_access(team, "write", frappe.session.user):
			CannotManageEvent.throw()
		self.event = event

	def save(self, ticket_types: list[TicketTypeInput]) -> EventTicketTypes:
		self.delete_missing({row.name for row in ticket_types if row.name})
		for row in ticket_types:
			self.upsert(row)
		return event_ticket_types(self.event)

	def delete_missing(self, kept: set[str]) -> None:
		existing = frappe.get_all(
			"Event Ticket Type", filters={"event": self.event}, fields=["name", "title"]
		)
		sold = tickets_sold_by_type(self.event)
		for row in existing:
			if str(row.name) in kept:
				continue
			if sold.get(str(row.name)):
				TicketTypeHasSales.throw(title=row.title)
			frappe.delete_doc("Event Ticket Type", row.name)

	def upsert(self, row: TicketTypeInput) -> None:
		doc = (
			self.existing_doc(row.name) if row.name else frappe.new_doc("Event Ticket Type", event=self.event)
		)
		doc.update(row.model_dump(exclude={"name", "prices"}))
		doc.set("prices", [price.model_dump() for price in row.prices])
		doc.save()

	def existing_doc(self, name: str):
		event = frappe.db.get_value("Event Ticket Type", name, "event")
		if str(event) != str(self.event):
			TicketTypeNotFound.throw()
		return frappe.get_doc("Event Ticket Type", name)
