import frappe
from frappe.query_builder.functions import Count, Date, Sum
from frappe.utils import flt

from buzz.api.events.ticket_types import paid_bookings, revenue_by_currency
from buzz.api.transactions.schemas import (
	CurrencySummary,
	DailyRevenue,
	PaymentMethodTotal,
	PendingVerification,
	TransactionSummary,
)
from buzz.api.transactions.services import (
	VERIFICATION_PENDING,
	ensure_transactions_access,
	latest_payments,
	payment_method_of,
)


def transaction_summary(event: str) -> TransactionSummary:
	ensure_transactions_access(event)
	event = str(event)
	return TransactionSummary(
		currencies=currency_summaries(event),
		pending_verification=pending_verification(event),
		by_payment_method=totals_by_payment_method(event),
		daily=daily_revenue(event),
	)


def currency_summaries(event: str) -> list[CurrencySummary]:
	summaries = []
	for revenue in revenue_by_currency(event):
		net = flt(revenue.collected) - flt(revenue.refunded)
		average = flt(revenue.collected) / revenue.bookings if revenue.bookings else 0
		summaries.append(CurrencySummary(**revenue.model_dump(), net=net, average_order_value=average))
	return summaries


def daily_revenue(event: str) -> list[DailyRevenue]:
	"""Paid bookings by the day they were made; a later refund counts against that day."""
	booking = frappe.qb.DocType("Event Booking")
	day = Date(booking.creation)
	rows = (
		paid_bookings(event)
		.select(
			day.as_("date"),
			booking.currency,
			Sum(booking.total_amount).as_("collected"),
			Sum(booking.refunded_amount).as_("refunded"),
			Count(booking.name).as_("bookings"),
		)
		.groupby(day, booking.currency)
		.orderby(day)
	).run(as_dict=True)
	return [DailyRevenue(**row) for row in rows]


def pending_verification(event: str) -> list[PendingVerification]:
	booking = frappe.qb.DocType("Event Booking")
	rows = (
		frappe.qb.from_(booking)
		.select(
			booking.currency,
			Count(booking.name).as_("bookings"),
			Sum(booking.total_amount).as_("amount"),
		)
		.where(
			(booking.event == event)
			& (booking.docstatus == 0)
			& (booking.payment_status == VERIFICATION_PENDING)
			& (booking.total_amount > 0)
		)
		.groupby(booking.currency)
	).run(as_dict=True)
	return [PendingVerification(**row) for row in rows]


def totals_by_payment_method(event: str) -> list[PaymentMethodTotal]:
	"""Grouped here: the method is the gateway of each booking's latest payment, not a column."""
	booking = frappe.qb.DocType("Event Booking")
	bookings = (
		paid_bookings(event).select(
			booking.name,
			booking.currency,
			booking.total_amount,
			booking.payment_method,
			booking.offline_payment_method,
		)
	).run(as_dict=True)
	payments = latest_payments([row.name for row in bookings])
	totals: dict[tuple, PaymentMethodTotal] = {}
	for row in bookings:
		method = payment_method_of(row, payments.get(row.name))
		total = totals.setdefault(
			(row.currency, method),
			PaymentMethodTotal(currency=row.currency, payment_method=method, bookings=0, amount=0),
		)
		total.bookings += 1
		total.amount += flt(row.total_amount)
	return sorted(totals.values(), key=lambda total: (total.currency or "", -total.amount))
