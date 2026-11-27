import frappe
from frappe.query_builder.functions import Count, Sum
from frappe.utils import flt

from buzz.api.booking.cache import invalidate_event_booking_cache
from buzz.api.booking.services import are_registrations_closed
from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.events.schemas import (
	AddOnItem,
	CurrencyRevenue,
	EventTicketTypes,
	PaymentProviderItem,
	TicketCategoryItem,
	TicketTypeItem,
	TicketTypePrice,
)
from buzz.api.events.services import get_event_doc, manageable_event, registration_link
from buzz.api.events.taxes import team_tax_details
from buzz.events.doctype.buzz_form.form_types import REGISTRATION_FORM_DOCTYPE, is_registration_closed
from buzz.payments import get_payment_gateways_for_event
from buzz.permissions import event_section_permissions
from buzz.ticketing.doctype.event_ticket_category.event_ticket_category import get_ordered_categories
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import tickets_sold_by_currency
from buzz.ticketing.doctype.ticket_add_on.ticket_add_on import add_on_options

TICKET_TYPE_FIELDS = [
	"name",
	"title",
	"description",
	"category",
	"max_tickets_available",
	"auto_unpublish_after",
	"is_published",
	"is_hidden",
	"requires_approval",
	"enable_waitlist",
	{"prices": ["currency", "price"]},
]

ADD_ON_FIELDS = [
	"name",
	"title",
	"description",
	"price",
	"currency",
	"enabled",
	"user_selects_option",
	"options",
	{"ticket_types": ["ticket_type"]},
]


def event_ticket_types(event: str) -> EventTicketTypes:
	doc = get_event_doc(event)
	event_id = str(doc.name)
	perms = event_section_permissions(event_id, "ticketing", team=doc.team or "")
	if not perms["can_read"]:
		CannotManageEvent.throw()
	rows = ticket_type_rows(event_id)
	sold = tickets_sold_by_type(event_id) if rows else {}
	sold_by_currency = tickets_sold_by_currency([row.name for row in rows]) if sold else {}
	form = frappe.qb.DocType("Buzz Form")
	reg_forms = (
		frappe.qb.from_(form)
		.select(form.name, form.publish, form.auto_close_at)
		.where((form.event == event_id) & (form.form_doctype == REGISTRATION_FORM_DOCTYPE))
		.limit(1)
	).run(as_dict=True)
	reg_form = reg_forms[0] if reg_forms else None
	return EventTicketTypes(
		title=doc.title,
		can_write=perms["can_write"],
		registration_link=registration_link(doc),
		registration_form=reg_form.name if reg_form else None,
		registrations_closed=is_registration_closed(reg_form, doc),
		allow_guest_booking=bool(doc.allow_guest_booking),
		guest_verification_method=doc.guest_verification_method or "None",
		requires_approval=bool(doc.requires_approval),
		enable_waitlist=bool(doc.enable_waitlist),
		apply_tax=bool(doc.apply_tax),
		tax_inclusive=bool(doc.tax_inclusive),
		# Same defaults as Buzz Event's validate_tax_settings, so the form opens filled in.
		tax_label=doc.tax_label or "GST",
		tax_percentage=flt(doc.tax_percentage) or 18,
		**visible_tax_details(doc.team, has_team_read=perms["has_team_read"]),
		can_edit_team=perms["can_edit_team"],
		categories=ticket_categories(event_id),
		ticket_types=[ticket_type_item(row, sold, sold_by_currency) for row in rows],
		add_ons=add_on_items(event_id),
		payment_providers=payment_providers(event_id, event_doc=doc),
		revenue=revenue_by_currency(event_id),
	)


def ticket_type_rows(event: str) -> list[frappe._dict]:
	tt = frappe.qb.DocType("Event Ticket Type")
	rows = (
		frappe.qb.from_(tt)
		.select(
			tt.name,
			tt.title,
			tt.description,
			tt.category,
			tt.max_tickets_available,
			tt.auto_unpublish_after,
			tt.is_published,
			tt.is_hidden,
			tt.requires_approval,
			tt.enable_waitlist,
		)
		.where(tt.event == event)
		.orderby(tt.creation)
	).run(as_dict=True)
	if not rows:
		return []
	price = frappe.qb.DocType("Buzz Price")
	price_rows = (
		frappe.qb.from_(price)
		.select(price.parent, price.currency, price.price)
		.where(
			(price.parenttype == "Event Ticket Type")
			& (price.parentfield == "prices")
			& price.parent.isin([str(row.name) for row in rows])
		)
		.orderby(price.idx)
	).run(as_dict=True)
	prices_by_parent: dict[str, list] = {}
	for row in price_rows:
		prices_by_parent.setdefault(str(row.parent), []).append(
			frappe._dict(currency=row.currency, price=row.price)
		)
	for row in rows:
		row["prices"] = prices_by_parent.get(str(row.name), [])
	return rows


def visible_tax_details(team: str, has_team_read: bool = True) -> dict:
	"""The team's legal identity stays with its members; a collaborator only works on the event."""
	details = team_tax_details(team)
	has_details = bool(details["team_tax_id"])
	if not has_team_read:
		details = {"team_legal_name": None, "team_tax_id": None}
	return details | {"has_team_tax_details": has_details}


def ticket_categories(event: str) -> list[TicketCategoryItem]:
	return [TicketCategoryItem(**row) for row in get_ordered_categories(event)]


def payment_providers(event: str, event_doc=None) -> list[PaymentProviderItem]:
	gateways = get_payment_gateways_for_event(event, event_doc=event_doc)
	if not gateways:
		return []
	default = frappe.get_cached_value("Buzz Settings", "Buzz Settings", "default_payment_gateway")
	return [PaymentProviderItem(name=gateway, is_default=gateway == default) for gateway in gateways]


def ticket_type_item(row, sold: dict, sold_by_currency: dict) -> TicketTypeItem:
	name = str(row.name)
	prices = [
		TicketTypePrice(**price, tickets_sold=sold_by_currency.get((name, price.currency), 0))
		for price in row.prices
	]
	return TicketTypeItem(**{**row, "name": name, "tickets_sold": sold.get(name, 0), "prices": prices})


def add_on_items(event: str) -> list[AddOnItem]:
	addon = frappe.qb.DocType("Ticket Add-on")
	rows = (
		frappe.qb.from_(addon)
		.select(
			addon.name,
			addon.title,
			addon.description,
			addon.price,
			addon.currency,
			addon.enabled,
			addon.user_selects_option,
			addon.options,
		)
		.where(addon.event == event)
		.orderby(addon.title)
	).run(as_dict=True)
	if not rows:
		return []
	scope = frappe.qb.DocType("Ticket Add-on Ticket Type")
	scope_rows = (
		frappe.qb.from_(scope)
		.select(scope.parent, scope.ticket_type)
		.where((scope.parenttype == "Ticket Add-on") & scope.parent.isin([row.name for row in rows]))
		.orderby(scope.idx)
	).run(as_dict=True)
	by_parent: dict[str, list[str]] = {}
	for row in scope_rows:
		by_parent.setdefault(row.parent, []).append(str(row.ticket_type))
	return [
		AddOnItem(
			**{**row, "options": add_on_options(row.options), "ticket_types": by_parent.get(row.name, [])}
		)
		for row in rows
	]


def tickets_sold_by_type(event: str) -> dict[str, int]:
	ticket = frappe.qb.DocType("Event Ticket")
	rows = (
		frappe.qb.from_(ticket)
		.select(ticket.ticket_type, Count(ticket.name))
		.where((ticket.event == event) & (ticket.docstatus == 1))
		.groupby(ticket.ticket_type)
	).run()
	return {str(ticket_type): count for ticket_type, count in rows}


def revenue_by_currency(event: str) -> list[CurrencyRevenue]:
	booking = frappe.qb.DocType("Event Booking")
	rows = (
		paid_bookings(event)
		.select(
			booking.currency,
			Sum(booking.total_amount).as_("collected"),
			Sum(booking.refunded_amount).as_("refunded"),
			Sum(booking.tax_amount).as_("tax"),
			Sum(booking.discount_amount).as_("discounts"),
			Count(booking.name).as_("bookings"),
		)
		.groupby(booking.currency)
	).run(as_dict=True)
	if not rows:
		return []
	tickets = tickets_by_currency(event)
	return [CurrencyRevenue(**row, tickets=tickets.get(row.currency, 0)) for row in rows]


def tickets_by_currency(event: str) -> dict[str, int]:
	booking = frappe.qb.DocType("Event Booking")
	ticket = frappe.qb.DocType("Event Ticket")
	rows = (
		paid_bookings(event)
		.join(ticket)
		.on(ticket.booking == booking.name)
		.where((ticket.event == str(event)) & (ticket.docstatus == 1))
		.select(booking.currency, Count(ticket.name))
		.groupby(booking.currency)
	).run()
	return dict(rows)


def paid_bookings(event: str):
	"""An offline booking awaiting approval is submitted but not yet money; free ones never are."""
	booking = frappe.qb.DocType("Event Booking")
	return frappe.qb.from_(booking).where(
		(booking.event == event)
		& (booking.docstatus == 1)
		& (booking.payment_status == "Paid")
		& (booking.total_amount > 0)
	)


class TicketTypeAccess:
	"""Approval and waitlist for one ticket type. The event's flag stands for every ticket
	type, so turning one off while it is set moves the flag onto all the others instead."""

	def __init__(self, ticket_type: str):
		doc = frappe.get_doc("Event Ticket Type", ticket_type)
		self.ticket_type = str(doc.name)
		# Locked before reading, so two opt-outs at once can't both move the event flag.
		frappe.db.get_value("Buzz Event", doc.event, "name", for_update=True)
		self.event = manageable_event(doc.event, "ticketing")

	def update(self, requires_approval: bool, enable_waitlist: bool) -> None:
		self.set("requires_approval", requires_approval)
		self.set("enable_waitlist", enable_waitlist)
		invalidate_event_booking_cache(self.event.name)

	def set(self, field: str, enabled: bool) -> None:
		if not enabled and self.event.get(field):
			self.event.db_set(field, 0)
			for name in self.other_ticket_types():
				frappe.db.set_value("Event Ticket Type", name, field, 1)
		frappe.db.set_value("Event Ticket Type", self.ticket_type, field, int(enabled))

	def other_ticket_types(self) -> list[str]:
		filters = {"event": self.event.name, "name": ["!=", self.ticket_type]}
		return frappe.get_all("Event Ticket Type", filters=filters, pluck="name")
