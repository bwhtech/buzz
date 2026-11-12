import frappe
from frappe.utils import flt

from buzz.api.booking.details import coupon_code_of
from buzz.api.events.services import add_ons_by_ticket, titles_of
from buzz.api.transactions.exceptions import TransactionNotFound
from buzz.api.transactions.schemas import (
	TransactionAmounts,
	TransactionBuyer,
	TransactionDetail,
	TransactionLineItem,
	TransactionPayment,
	TransactionRefund,
	TransactionTicket,
	TransactionUTM,
)
from buzz.api.transactions.services import (
	ensure_transactions_access,
	latest_payments,
	payment_method_of,
	transaction_names,
)

PAYMENT_FIELDS = [
	"name",
	"payment_gateway",
	"payment_id",
	"order_id",
	"amount",
	"currency",
	"payment_received",
]


def with_created_at(row: dict) -> dict:
	row["created_at"] = row.pop("creation")
	return row


def add_on_labels(parenttype: str, parents: list[str]) -> dict[str, list[str]]:
	by_parent = add_ons_by_ticket([parent for parent in parents if parent], parenttype)
	return {
		parent: [f"{add_on.title}: {add_on.value}" if add_on.value else add_on.title for add_on in add_ons]
		for parent, add_ons in by_parent.items()
	}


class TransactionDetailBuilder:
	"""Everything the drawer shows about one booking of the event."""

	def __init__(self, event: str, booking: str):
		ensure_transactions_access(event)
		if not transaction_names(event, [["name", "=", booking]]):
			TransactionNotFound.throw()
		self.booking = frappe.get_doc("Event Booking", booking)

	def detail(self) -> TransactionDetail:
		booking = self.booking
		payment = latest_payments([booking.name]).get(booking.name)
		return TransactionDetail(
			name=booking.name,
			created_at=booking.creation,
			modified_at=booking.modified,
			currency=booking.currency,
			payment_status=booking.payment_status,
			refund_status=booking.refund_status or None,
			status=booking.status,
			payment_method=payment_method_of(booking, payment),
			offline_payment_method=booking.offline_payment_method,
			buyer=self.buyer(),
			amounts=self.amounts(),
			line_items=self.line_items(),
			payments=self.payments(),
			refunds=self.refunds(),
			tickets=self.tickets(),
			utm=[TransactionUTM(utm_name=row.utm_name, value=row.value) for row in booking.utm_parameters],
			answers=[row.as_dict(no_default_fields=True) for row in booking.additional_fields],
		)

	def buyer(self) -> TransactionBuyer:
		booking = self.booking
		return TransactionBuyer(
			name=booking.buyer_name,
			email=booking.buyer_email,
			phone=booking.buyer_phone,
			user=booking.user,
			business_name=booking.business_name,
			tax_id=booking.tax_id,
			billing_state=booking.billing_state,
			billing_address=booking.billing_address,
			invoice_requested=bool(booking.invoice_requested),
		)

	def amounts(self) -> TransactionAmounts:
		booking = self.booking
		access_code = booking.access_code
		return TransactionAmounts(
			net_amount=flt(booking.net_amount),
			discount_amount=flt(booking.discount_amount),
			coupon_code=coupon_code_of(booking),
			access_code=frappe.db.get_value("Buzz Coupon Code", access_code, "code") if access_code else None,
			tax_label=booking.tax_label,
			tax_percentage=flt(booking.tax_percentage),
			tax_amount=flt(booking.tax_amount),
			total_amount=flt(booking.total_amount),
			refunded_amount=flt(booking.refunded_amount),
			net_received=flt(booking.total_amount) - flt(booking.refunded_amount),
		)

	def line_items(self) -> list[TransactionLineItem]:
		attendees = self.booking.attendees
		titles = titles_of("Event Ticket Type", {row.ticket_type for row in attendees})
		add_ons = add_on_labels("Attendee Ticket Add-on", [row.add_ons for row in attendees])
		return [
			TransactionLineItem(
				attendee_name=row.full_name,
				attendee_email=row.email,
				ticket_type=titles.get(str(row.ticket_type)) or row.ticket_type,
				amount=flt(row.amount),
				add_ons=add_ons.get(row.add_ons, []),
				add_on_total=flt(row.add_on_total),
			)
			for row in attendees
		]

	def payments(self) -> list[TransactionPayment]:
		rows = frappe.get_all(
			"Event Payment",
			filters={"reference_doctype": "Event Booking", "reference_docname": self.booking.name},
			fields=[*PAYMENT_FIELDS, "creation"],
			order_by="creation desc",
		)
		return [
			TransactionPayment(
				**with_created_at(row)
				| {"name": str(row.name), "payment_received": bool(row.payment_received)}
			)
			for row in rows
		]

	def refunds(self) -> list[TransactionRefund]:
		rows = frappe.get_all(
			"Event Booking Refund",
			filters={"booking": self.booking.name},
			fields=["name", "refund_id", "amount", "status", "creation", "cancellation_request"],
			order_by="creation desc",
		)
		tickets = refunded_tickets([row.name for row in rows])
		return [
			TransactionRefund(**with_created_at(row) | {"tickets": tickets.get(row.name, [])}) for row in rows
		]

	def tickets(self) -> list[TransactionTicket]:
		rows = frappe.get_all(
			"Event Ticket",
			filters={"booking": self.booking.name, "docstatus": 1},
			fields=["name", "attendee_name", "attendee_email", "ticket_type"],
			order_by="creation asc",
		)
		names = [row.name for row in rows]
		titles = titles_of("Event Ticket Type", {row.ticket_type for row in rows})
		add_ons = add_on_labels("Event Ticket", names)
		checked_in = checked_in_tickets(names)
		return [
			TransactionTicket(
				**row
				| {
					"ticket_type": titles.get(str(row.ticket_type)) or row.ticket_type,
					"add_ons": add_ons.get(row.name, []),
					"checked_in": row.name in checked_in,
				}
			)
			for row in rows
		]


def refunded_tickets(refunds: list[str]) -> dict[str, list[str]]:
	if not refunds:
		return {}
	rows = frappe.get_all(
		"Event Booking Refund Ticket",
		filters={"parenttype": "Event Booking Refund", "parent": ("in", refunds)},
		fields=["parent", "ticket"],
		order_by="idx asc",
	)
	by_refund: dict[str, list[str]] = {}
	for row in rows:
		by_refund.setdefault(row.parent, []).append(row.ticket)
	return by_refund


def checked_in_tickets(tickets: list[str]) -> set[str]:
	if not tickets:
		return set()
	return set(
		frappe.get_all("Event Check In", filters={"ticket": ("in", tickets), "docstatus": 1}, pluck="ticket")
	)
