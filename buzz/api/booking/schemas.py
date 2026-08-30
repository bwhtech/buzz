from datetime import date, datetime, timedelta
from typing import Any

from pydantic import Field

from buzz.api.schemas import APIRequest, APIResponse


class BookingRequest(APIRequest):
	# attendees and custom fields carry event-defined dynamic keys; validated against meta downstream.
	attendees: list[dict]
	event: str
	coupon_code: str | None = None
	booking_custom_fields: dict | None = None
	payment_gateway: str | None = None
	utm_parameters: list[dict] | None = None
	guest_email: str | None = None
	guest_full_name: str | None = None
	otp: str | None = None
	guest_phone: str | None = None
	payment_proof: str | None = None
	is_offline: bool = False
	offline_payment_method: str | None = None
	invoice_requested: bool = False
	tax_id: str | None = None
	billing_address: str | None = None


class FreeBookingResponse(APIResponse):
	booking_name: str
	redirect_to: str


class OfflineBookingResponse(APIResponse):
	booking_name: str
	offline_payment: bool


class PaymentLinkResponse(APIResponse):
	payment_link: str


class TaxSettings(APIResponse):
	apply_tax: int
	tax_inclusive: int
	tax_label: str
	tax_percentage: float


class EventBookingDataResponse(APIResponse):
	# event_details and the list fields carry documents or meta-defined rows; typing
	# them would reshape the payload.
	registrations_closed: bool
	event_details: Any
	available_ticket_types: list
	available_add_ons: list
	tax_settings: TaxSettings
	custom_fields: list
	payment_gateways: list[str]
	offline_payment_enabled: bool
	offline_methods: list


class ConfirmationEvent(APIResponse):
	title: str | None
	route: str | None
	start_date: date | None
	end_date: date | None
	start_time: timedelta | None
	end_time: timedelta | None
	short_description: str | None
	free_event: int | None


class ConfirmationVenue(APIResponse):
	name: Any
	address: str | None


class ConfirmationBooking(APIResponse):
	name: str
	total_amount: float | None
	net_amount: float | None
	currency: str | None
	payment_status: str | None
	status: str | None
	tax_amount: float | None
	tax_label: str | None
	tax_percentage: float | None
	discount_amount: float | None
	coupon_code: str | None


class ConfirmationTicket(APIResponse):
	name: str
	attendee_name: str | None
	attendee_email: str | None
	ticket_type: str | None
	qr_code: str | None


class BookingConfirmationResponse(APIResponse):
	event: ConfirmationEvent
	venue: ConfirmationVenue | None
	booking: ConfirmationBooking
	tickets: list[ConfirmationTicket]


class BookingDetailsResponse(APIResponse):
	# doc, event, venue and the ticket rows are documents or aliased query rows;
	# they pass through untyped to keep the wire shape.
	doc: Any
	tickets: list
	event: Any
	venue: Any
	can_transfer_ticket: bool
	can_change_add_ons: bool
	can_request_cancellation: bool
	cancellation_request: Any
	cancellation_requested_tickets: list[str]
	cancelled_tickets: list[str]


class InvalidCouponResponse(APIResponse):
	valid: bool
	error: str | None


class DiscountCouponResponse(APIResponse):
	valid: bool
	coupon_type: str
	discount_type: str | None
	discount_value: float | None
	# `or 0` fallbacks put a literal int 0 on the wire; a plain float would coerce it to 0.0.
	max_discount_amount: int | float
	min_order_value: int | float


class FreeTicketsCouponResponse(APIResponse):
	valid: bool
	coupon_type: str
	ticket_type: Any
	remaining_tickets: int
	free_add_ons: list


class BookingLine(APIResponse):
	"""One ticket type on a booking. Its add-ons hang off it and never nest further."""

	label: str
	quantity: int
	# Attendee amounts only — every add-on carries its own.
	amount: float
	add_ons: list["BookingLine"] = Field(default_factory=list)


class BookingSummary(APIResponse):
	"""A booking as a receipt: what was bought and what it cost, and nothing else.

	No ticket, attendee or QR field travels — the card draws none of them, and the reader
	is always the person who booked.
	"""

	name: str
	status: str
	payment_status: str
	payment_method: str | None
	is_offline: bool
	currency: str
	booked_on: datetime
	lines: list[BookingLine]
	net_amount: float
	discount_amount: float
	coupon_code: str | None
	tax_amount: float
	tax_label: str | None
	tax_percentage: float
	total_amount: float
