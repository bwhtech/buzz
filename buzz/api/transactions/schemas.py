from datetime import date, datetime
from typing import Any

from buzz.api.events.schemas import CurrencyRevenue
from buzz.api.filters.schemas import FilterField
from buzz.api.schemas import APIResponse


class TransactionRow(APIResponse):
	name: str
	created_at: datetime
	buyer_name: str | None = None
	buyer_email: str | None = None
	tickets: int
	total_amount: float
	currency: str | None = None
	payment_method: str | None = None
	payment_status: str | None = None
	refund_status: str | None = None
	payment_id: str | None = None


class TransactionsPage(APIResponse):
	title: str | None = None
	currencies: list[str]
	total: int
	matched: int
	transactions: list[TransactionRow]
	has_next_page: bool
	filter_fields: list[FilterField]


class TransactionBuyer(APIResponse):
	name: str | None = None
	email: str | None = None
	phone: str | None = None
	user: str | None = None
	business_name: str | None = None
	tax_id: str | None = None
	billing_state: str | None = None
	billing_address: str | None = None
	invoice_requested: bool


class TransactionAmounts(APIResponse):
	net_amount: float
	discount_amount: float
	coupon_code: str | None = None
	access_code: str | None = None
	tax_label: str | None = None
	tax_percentage: float
	tax_amount: float
	total_amount: float
	refunded_amount: float
	net_received: float


class TransactionLineItem(APIResponse):
	attendee_name: str | None = None
	attendee_email: str | None = None
	ticket_type: str | None = None
	amount: float
	add_ons: list[str]
	add_on_total: float


class TransactionPayment(APIResponse):
	name: str
	payment_gateway: str | None = None
	payment_id: str | None = None
	order_id: str | None = None
	amount: float
	currency: str | None = None
	payment_received: bool
	created_at: datetime


class TransactionRefund(APIResponse):
	name: str
	refund_id: str | None = None
	amount: float
	status: str | None = None
	created_at: datetime
	tickets: list[str]
	cancellation_request: str | None = None


class TransactionTicket(APIResponse):
	name: str
	attendee_name: str | None = None
	attendee_email: str | None = None
	ticket_type: str | None = None
	add_ons: list[str]
	checked_in: bool


class TransactionUTM(APIResponse):
	utm_name: str | None = None
	value: str | None = None


class TransactionDetail(APIResponse):
	name: str
	created_at: datetime
	modified_at: datetime
	currency: str | None = None
	payment_status: str | None = None
	refund_status: str | None = None
	status: str | None = None
	payment_method: str | None = None
	offline_payment_method: str | None = None
	buyer: TransactionBuyer
	amounts: TransactionAmounts
	line_items: list[TransactionLineItem]
	payments: list[TransactionPayment]
	refunds: list[TransactionRefund]
	tickets: list[TransactionTicket]
	utm: list[TransactionUTM]
	# Additional Field rows as saved, whose shape follows each event's form.
	answers: list[Any]


class CurrencySummary(CurrencyRevenue):
	net: float
	average_order_value: float


class PendingVerification(APIResponse):
	currency: str | None = None
	bookings: int
	amount: float


class PaymentMethodTotal(APIResponse):
	currency: str | None = None
	payment_method: str | None = None
	bookings: int
	amount: float


class DailyRevenue(APIResponse):
	date: date
	currency: str | None = None
	collected: float
	refunded: float
	bookings: int


class TransactionSummary(APIResponse):
	currencies: list[CurrencySummary]
	daily: list[DailyRevenue]
	pending_verification: list[PendingVerification]
	by_payment_method: list[PaymentMethodTotal]
