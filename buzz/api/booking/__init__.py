import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.booking import coupons, details, event_data, guests
from buzz.api.booking.schemas import (
	BookingConfirmationResponse,
	BookingDetailsResponse,
	BookingRequest,
	BookingSummary,
	EventBookingDataResponse,
	FreeBookingResponse,
	OfflineBookingResponse,
	PaymentLinkResponse,
)
from buzz.api.booking.services import BookingService


# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="identifier", limit=5, seconds=3600)
def send_guest_booking_otp(event: int, identifier: str) -> dict | None:
	return guests.send_booking_otp(event, identifier)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_event_booking_data(event_route: str) -> EventBookingDataResponse:
	return event_data.build_event_booking_data(event_route)


# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def process_booking(
	booking: BookingRequest,
) -> FreeBookingResponse | OfflineBookingResponse | PaymentLinkResponse:
	return BookingService(booking).process()


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_booking_confirmation(booking_id: str, token: str | None = None) -> BookingConfirmationResponse:
	return details.build_booking_confirmation(booking_id, token)


@frappe.whitelist()
def get_booking_details(booking_id: str) -> BookingDetailsResponse:
	return details.build_booking_details(booking_id)


@frappe.whitelist()
def get_my_booking_summaries(event: str) -> list[BookingSummary]:
	"""Every booking the session user made for one event, each as a receipt."""
	return details.build_my_booking_summaries(event)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def validate_coupon(coupon_code: str, event: str, user_email: str | None = None) -> coupons.CouponResponse:
	return coupons.validate_coupon_for_event(coupon_code, event, user_email)
