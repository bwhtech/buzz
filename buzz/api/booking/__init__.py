import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.booking import coupons, details, downloads, event_data, guests, my_bookings
from buzz.api.booking.holds import TicketHoldService
from buzz.api.booking.schemas import (
	BookingConfirmationResponse,
	BookingDetailsResponse,
	BookingRequest,
	BookingSummary,
	EventBookingDataResponse,
	FreeBookingResponse,
	MyBooking,
	OfflineBookingResponse,
	PaymentLinkResponse,
	TicketHoldResponse,
)
from buzz.api.booking.services import BookingService
from buzz.ticketing.doctype.ticket_hold import ticket_hold


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="identifier", limit=5, seconds=3600)
def send_guest_booking_otp(event: int, identifier: str) -> dict | None:
	return guests.send_booking_otp(event, identifier)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_event_booking_data(event_route: str, hold_token: str | None = None) -> EventBookingDataResponse:
	return event_data.build_event_booking_data(event_route, hold_token)


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def process_booking(
	booking: BookingRequest,
) -> FreeBookingResponse | OfflineBookingResponse | PaymentLinkResponse:
	return BookingService(booking).process()


def hold_tickets_rate_limit() -> int:
	return 60 if frappe.session.user == "Guest" else 300


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=hold_tickets_rate_limit, seconds=600)
def hold_tickets(event: int, quantities: dict, hold_token: str | None = None) -> TicketHoldResponse:
	return TicketHoldService(event, quantities, hold_token).hold()


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def release_hold(hold_token: str) -> None:
	ticket_hold.release_hold(hold_token)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_booking_confirmation(booking_id: str, token: str | None = None) -> BookingConfirmationResponse:
	return details.build_booking_confirmation(booking_id, token)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_calendar_invite(booking_id: str, token: str | None = None) -> None:
	downloads.calendar_invite(booking_id, token)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def download_tickets(booking_id: str, token: str | None = None) -> None:
	downloads.tickets_pdf(booking_id, token)


@frappe.whitelist()
def get_booking_details(booking_id: str) -> BookingDetailsResponse:
	return details.build_booking_details(booking_id)


@frappe.whitelist()
def get_my_bookings() -> list[MyBooking]:
	return my_bookings.my_bookings()


@frappe.whitelist()
def get_booking_summary(booking_id: str) -> BookingSummary:
	"""One booking as a receipt, for anyone allowed to read it."""
	return details.build_booking_summary(booking_id)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def validate_coupon(
	coupon_code: str, event: str, user_email: str | None = None, currency: str | None = None
) -> coupons.CouponResponse:
	return coupons.validate_coupon_for_event(coupon_code, event, user_email, currency)
