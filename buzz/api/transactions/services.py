import frappe
from frappe.query_builder import Order
from frappe.query_builder.functions import Count

from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD
from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.events.services import get_event_doc
from buzz.api.filters.exceptions import InvalidFilter
from buzz.api.transactions.filters import TransactionConditions, transaction_filter_fields
from buzz.api.transactions.schemas import TransactionRow, TransactionsPage
from buzz.permissions import can_view_transactions

VERIFICATION_PENDING = "Verification Pending"
ROW_FIELDS = [
	"name",
	"creation",
	"buyer_name",
	"buyer_email",
	"total_amount",
	"currency",
	"payment_method",
	"offline_payment_method",
	"payment_status",
	"refund_status",
]


def ensure_transactions_access(event: str):
	doc = get_event_doc(event)
	if not can_view_transactions(event, team=doc.team or ""):
		CannotManageEvent.throw()
	return doc


def transaction_filters(event: str) -> list[list]:
	"""A paid-for booking on the event: submitted, or offline and awaiting verification."""
	return [["event", "=", str(event)], ["total_amount", ">", 0], ["docstatus", "!=", 2]]


# The list's status tabs. Paid leaves out refunds, which have a tab of their own.
STATUS_FILTERS = {
	"paid": [["payment_status", "=", "Paid"], ["refund_status", "is", "not set"]],
	"pending": [["payment_status", "=", VERIFICATION_PENDING]],
	"refunded": [["refund_status", "is", "set"]],
}

TRANSACTION_OR_FILTERS = [["docstatus", "=", 1], ["payment_status", "=", VERIFICATION_PENDING]]


def transaction_names(event: str, filters: list[list] | None = None, **arguments) -> list[str]:
	return frappe.get_all(
		"Event Booking",
		filters=[*transaction_filters(event), *(filters or [])],
		or_filters=TRANSACTION_OR_FILTERS,
		pluck="name",
		**arguments,
	)


def count_transactions(event: str, filters: list[list] | None = None) -> int:
	rows = frappe.get_all(
		"Event Booking",
		filters=[*transaction_filters(event), *(filters or [])],
		or_filters=TRANSACTION_OR_FILTERS,
		fields=[{"COUNT": "*"}],
	)
	return rows[0]["COUNT(*)"] if rows else 0


def latest_payments(bookings: list[str]) -> dict[str, frappe._dict]:
	"""Each booking's most recent Event Payment, in one query."""
	if not bookings:
		return {}
	payment = frappe.qb.DocType("Event Payment")
	rows = (
		frappe.qb.from_(payment)
		.select(payment.reference_docname, payment.payment_gateway, payment.payment_id)
		.where((payment.reference_doctype == "Event Booking") & payment.reference_docname.isin(bookings))
		.orderby(payment.creation)
		.orderby(payment.name)
	).run(as_dict=True)
	return {row.reference_docname: row for row in rows}


def payment_method_of(booking, payment) -> str | None:
	"""The offline method the buyer picked, else the gateway the payment went through."""
	if booking.payment_method == OFFLINE_PAYMENT_METHOD:
		return booking.offline_payment_method or booking.payment_method
	return (payment and payment.payment_gateway) or booking.payment_method


def ticket_counts(bookings: list[str]) -> dict[str, int]:
	if not bookings:
		return {}
	attendee = frappe.qb.DocType("Event Booking Attendee")
	rows = (
		frappe.qb.from_(attendee)
		.select(attendee.parent, Count("*"))
		.where((attendee.parenttype == "Event Booking") & attendee.parent.isin(bookings))
		.groupby(attendee.parent)
	).run()
	return dict(rows)


def event_currency_totals(event: str) -> tuple[list[str], int]:
	"""Distinct transaction currencies and total transaction count for `event`, in one query."""
	booking = frappe.qb.DocType("Event Booking")
	rows = (
		frappe.qb.from_(booking)
		.select(booking.currency, Count(booking.name))
		.where(
			(booking.event == str(event))
			& (booking.total_amount > 0)
			& (booking.docstatus != 2)
			& ((booking.docstatus == 1) | (booking.payment_status == VERIFICATION_PENDING))
		)
		.groupby(booking.currency)
		.orderby(booking.currency)
	).run()
	currencies = [currency for currency, _ in rows if currency]
	total = sum(count for _, count in rows)
	return currencies, total


class TransactionsList:
	"""One page of an event's transactions, searched, filtered and ordered by creation."""

	def __init__(
		self, event: str, search: str | None, filters: str | None, name: str | None, status: str | None = None
	):
		self.event_doc = ensure_transactions_access(event)
		self.event = str(self.event_doc.name)
		self.currencies, self.total = event_currency_totals(self.event)
		self.filter_fields = transaction_filter_fields(self.event, self.currencies)
		self.conditions = TransactionConditions(self.event, self.filter_fields).frappe_filters(filters)
		if term := (search or "").strip():
			self.conditions.append(["name", "in", searched_bookings(self.event, term) or [""]])
		if name:
			self.conditions.append(["name", "=", name])
		if status:
			if status not in STATUS_FILTERS:
				InvalidFilter.throw()
			self.conditions.extend(STATUS_FILTERS[status])

	def page(self, order: str, start: int, limit: int) -> TransactionsPage:
		limit = max(1, min(int(limit), 100))
		start = max(0, int(start))
		if not self.total:
			rows, matched = [], 0
		else:
			rows = self.rows(order, start, limit)
			if not self.conditions:
				matched = self.total
			elif start == 0 and len(rows) < limit:
				matched = len(rows)
			else:
				matched = count_transactions(self.event, self.conditions)
		return TransactionsPage(
			title=self.event_doc.title,
			currencies=self.currencies,
			total=self.total,
			matched=matched,
			transactions=rows,
			has_next_page=start + len(rows) < matched,
			filter_fields=self.filter_fields,
		)

	def rows(self, order: str, start: int, limit: int) -> list[TransactionRow]:
		# Interpolated into ORDER BY, so it can only ever be one of two literals.
		direction = "asc" if str(order).lower() == "asc" else "desc"
		if not self.conditions:
			booking = frappe.qb.DocType("Event Booking")
			order_dir = Order.asc if direction == "asc" else Order.desc
			bookings = (
				frappe.qb.from_(booking)
				.select(*(booking[field] for field in ROW_FIELDS))
				.where(
					(booking.event == self.event)
					& (booking.total_amount > 0)
					& (booking.docstatus != 2)
					& ((booking.docstatus == 1) | (booking.payment_status == VERIFICATION_PENDING))
				)
				.orderby(booking.creation, order=order_dir)
				.orderby(booking.name, order=order_dir)
				.limit(limit)
				.offset(start)
			).run(as_dict=True)
		else:
			bookings = frappe.get_all(
				"Event Booking",
				filters=[*transaction_filters(self.event), *self.conditions],
				or_filters=TRANSACTION_OR_FILTERS,
				fields=ROW_FIELDS,
				order_by=f"creation {direction}, name {direction}",
				limit_start=start,
				limit=limit,
			)
		names = [booking.name for booking in bookings]
		payments, tickets = latest_payments(names), ticket_counts(names)
		return [transaction_row(booking, payments, tickets) for booking in bookings]


def transaction_row(booking, payments: dict, tickets: dict) -> TransactionRow:
	payment = payments.get(booking.name)
	return TransactionRow(
		name=booking.name,
		created_at=booking.creation,
		buyer_name=booking.buyer_name,
		buyer_email=booking.buyer_email,
		tickets=tickets.get(booking.name, 0),
		total_amount=booking.total_amount,
		currency=booking.currency,
		payment_method=payment_method_of(booking, payment),
		payment_status=booking.payment_status,
		refund_status=booking.refund_status or None,
		payment_id=payment.payment_id if payment else None,
	)


def like_pattern(term: str) -> str:
	"""Typed % and _ are matched as themselves, not as wildcards."""
	escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return f"%{escaped}%"


def searched_bookings(event: str, term: str) -> list[str]:
	"""Bookings of the event matching on the buyer, the booking name, or a payment's ids."""
	event_id = str(event)
	booking = frappe.qb.DocType("Event Booking")
	payment = frappe.qb.DocType("Event Payment")
	payment_booking = frappe.qb.DocType("Event Booking").as_("payment_booking")
	pattern = like_pattern(term)
	paid_by = (
		frappe.qb.from_(payment)
		.join(payment_booking)
		.on(payment_booking.name == payment.reference_docname)
		.select(payment.reference_docname)
		.where(
			(payment_booking.event == event_id)
			& (payment.reference_doctype == "Event Booking")
			& (payment.payment_id.like(pattern) | payment.order_id.like(pattern))
		)
	)
	matches = (
		booking.name.like(pattern)
		| booking.buyer_name.like(pattern)
		| booking.buyer_email.like(pattern)
		| booking.buyer_phone.like(pattern)
		| booking.name.isin(paid_by)
	)
	query = frappe.qb.from_(booking).select(booking.name).where((booking.event == event_id) & matches)
	return query.orderby(booking.name, order=Order.asc).run(pluck=True)
