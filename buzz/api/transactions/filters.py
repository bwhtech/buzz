import frappe
from frappe import _
from frappe.utils import add_days

from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD
from buzz.api.events.services import ticket_types_of
from buzz.api.filters.conditions import ListConditions, filter_field
from buzz.api.filters.schemas import FilterField


def select_options(fieldname: str) -> list[tuple[str, str]]:
	options = frappe.get_meta("Event Booking").get_field(fieldname).options or ""
	return [(option, _(option)) for option in options.splitlines() if option.strip()]


def coupon_options(event: str) -> list[tuple[str, str]]:
	rows = frappe.get_all(
		"Buzz Coupon Code", filters={"event": event}, fields=["name", "code"], order_by="code asc"
	)
	return [(row.name, row.code or row.name) for row in rows]


def payment_method_options(event: str) -> list[tuple[str, str]]:
	"""Offline methods buyers picked and gateways payments went through, on this event."""
	offline = frappe.get_all(
		"Event Booking",
		filters={"event": event, "payment_method": OFFLINE_PAYMENT_METHOD},
		pluck="offline_payment_method",
		distinct=True,
	)
	gateways = frappe.get_all(
		"Event Payment",
		filters={
			"reference_doctype": "Event Booking",
			"reference_docname": ("in", event_bookings(event) or [""]),
		},
		pluck="payment_gateway",
		distinct=True,
	)
	return [(method, method) for method in sorted({*offline, *gateways} - {None, ""})]


def transaction_filter_fields(event: str, currencies: list[str]) -> list[FilterField]:
	fields = [
		filter_field("payment_status", _("Payment status"), "Select", select_options("payment_status")),
		filter_field("payment_method", _("Payment method"), "Select", payment_method_options(event)),
		filter_field("refund_status", _("Refund status"), "Select", select_options("refund_status")),
		filter_field(
			"ticket_type",
			_("Ticket type"),
			"Link",
			[(row.name, row.title or row.name) for row in ticket_types_of(event)],
		),
		filter_field("coupon_code", _("Coupon code"), "Link", coupon_options(event)),
		filter_field("creation", _("Created on"), "Date"),
		filter_field("invoice_requested", _("Invoice requested"), "Check", [("1", _("Yes")), ("0", _("No"))]),
	]
	if len(currencies) > 1:
		fields.insert(1, filter_field("currency", _("Currency"), "Select", [(c, c) for c in currencies]))
	return fields


def event_bookings(event: str):
	booking = frappe.qb.DocType("Event Booking")
	return frappe.qb.from_(booking).select(booking.name).where(booking.event == event).run(pluck=True)


class TransactionConditions(ListConditions):
	"""Booking filters, with the keys that live off the booking resolved to booking names."""

	def __init__(self, event: str, fields: list[FilterField]):
		super().__init__("Event Booking", fields)
		self.event = event

	def translate(self, key: str, operator: str, value) -> list | None:
		condition = super().translate(key, operator, value)
		if not condition:
			return None
		if key == "ticket_type":
			return ["name", operator, self.bookings_with_ticket_types(value) or [""]]
		if key == "payment_method":
			return ["name", operator, self.bookings_paid_by(value) or [""]]
		if key == "creation":
			return creation_condition(operator, value)
		return condition

	def bookings_with_ticket_types(self, ticket_types: list[str]) -> list[str]:
		attendee = frappe.qb.DocType("Event Booking Attendee")
		booking = frappe.qb.DocType("Event Booking")
		return (
			frappe.qb.from_(attendee)
			.join(booking)
			.on(booking.name == attendee.parent)
			.select(attendee.parent)
			.distinct()
			.where(
				(attendee.parenttype == "Event Booking")
				& (booking.event == self.event)
				& attendee.ticket_type.isin(ticket_types)
			)
		).run(pluck=True)

	def bookings_paid_by(self, methods: list[str]) -> list[str]:
		booking = frappe.qb.DocType("Event Booking")
		payment = frappe.qb.DocType("Event Payment")
		by_gateway = (
			frappe.qb.from_(payment)
			.select(payment.reference_docname)
			.where((payment.reference_doctype == "Event Booking") & payment.payment_gateway.isin(methods))
		)
		offline = (booking.payment_method == OFFLINE_PAYMENT_METHOD) & booking.offline_payment_method.isin(
			methods
		)
		online = booking.name.isin(by_gateway)
		return (
			frappe.qb.from_(booking)
			.select(booking.name)
			.where((booking.event == self.event) & (offline | online))
		).run(pluck=True)


def creation_condition(operator: str, value) -> list:
	"""`creation` is a timestamp, so a day compares against the whole of that day."""
	if operator == "=":
		return ["creation", "between", [value, value]]
	if operator == ">":
		return ["creation", ">=", add_days(value, 1)]
	return ["creation", operator, value]
