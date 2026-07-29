from datetime import date, datetime, timedelta

from buzz.api.schemas import APIResponse


class PaymentDetails(APIResponse):
	name: str
	amount: float
	currency: str | None


class TicketAddOn(APIResponse):
	add_on: str
	add_on_title: str | None
	add_on_selects_option: int | None
	value: str | None
	price: float | None
	currency: str | None


class TicketCheckinDetails(APIResponse):
	id: str
	attendee_name: str | None
	attendee_email: str | None
	event_title: str
	ticket_type: str | None
	venue: str | None
	start_date: date | None
	start_time: timedelta | None
	end_date: date | None
	end_time: timedelta | None
	is_checked_in: bool
	check_in_time: datetime | None
	booking_id: str | None
	add_ons: list[TicketAddOn]
	check_in_date: str | None = None


class CheckinResponse(APIResponse):
	message: str
	ticket: TicketCheckinDetails
	payment_details: PaymentDetails | None = None
