import frappe
from frappe.query_builder.functions import Count, Date, Sum
from frappe.utils import flt

from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD
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
)


def transaction_summary(event: str) -> TransactionSummary:
	ensure_transactions_access(event)
	event = str(event)
	currencies = currency_summaries(event)
	return TransactionSummary(
		currencies=currencies,
		pending_verification=pending_verification(event),
		by_payment_method=totals_by_payment_method(event) if currencies else [],
		daily=daily_revenue(event) if currencies else [],
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


PAYMENT_METHOD_TOTALS_SQL = """
	SELECT
		b.currency,
		CASE
			WHEN b.payment_method = %(offline)s
				THEN COALESCE(NULLIF(b.offline_payment_method, ''), b.payment_method)
			ELSE COALESCE(NULLIF(lp.payment_gateway, ''), b.payment_method)
		END AS payment_method,
		COUNT(b.name) AS bookings,
		SUM(b.total_amount) AS amount
	FROM `tabEvent Booking` b
	LEFT JOIN (
		SELECT reference_docname, payment_gateway
		FROM (
			SELECT
				p.reference_docname,
				p.payment_gateway,
				ROW_NUMBER() OVER (
					PARTITION BY p.reference_docname
					ORDER BY p.creation DESC, p.name DESC
				) AS rn
			FROM `tabEvent Payment` p
			INNER JOIN `tabEvent Booking` b2
				ON b2.name = p.reference_docname
			WHERE p.reference_doctype = 'Event Booking'
				AND b2.event = %(event)s
				AND b2.docstatus = 1
				AND b2.payment_status = 'Paid'
				AND b2.total_amount > 0
		) ranked
		WHERE ranked.rn = 1
	) lp ON lp.reference_docname = b.name
	WHERE b.event = %(event)s
		AND b.docstatus = 1
		AND b.payment_status = 'Paid'
		AND b.total_amount > 0
	GROUP BY b.currency, payment_method
	ORDER BY COALESCE(b.currency, '') ASC, amount DESC
"""


def totals_by_payment_method(event: str) -> list[PaymentMethodTotal]:
	"""Aggregate paid bookings in SQL by currency and each booking's latest payment gateway."""
	rows = frappe.db.sql(
		PAYMENT_METHOD_TOTALS_SQL,
		{"event": str(event), "offline": OFFLINE_PAYMENT_METHOD},
		as_dict=True,
	)
	return [
		PaymentMethodTotal(
			currency=row.currency,
			payment_method=row.payment_method,
			bookings=row.bookings,
			amount=flt(row.amount),
		)
		for row in rows
	]
