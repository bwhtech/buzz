import frappe
from frappe import _

from buzz.api.booking.schemas import (
	DiscountCouponResponse,
	FreeTicketsCouponResponse,
	InvalidCouponResponse,
)

CouponResponse = InvalidCouponResponse | DiscountCouponResponse | FreeTicketsCouponResponse


def validate_coupon_for_event(coupon_code: str, event: str, user_email: str | None) -> CouponResponse:
	if not frappe.db.exists("Buzz Coupon Code", coupon_code):
		return InvalidCouponResponse(valid=False, error=_("Invalid coupon code"))

	coupon = frappe.get_doc("Buzz Coupon Code", coupon_code)

	is_valid, error = coupon.is_valid_for_event(event)
	if not is_valid:
		return InvalidCouponResponse(valid=False, error=error)

	is_available, error = coupon.is_usage_available()
	if not is_available:
		return InvalidCouponResponse(valid=False, error=error)

	is_limited, error = coupon.is_user_limit_reached(user=resolve_coupon_user(user_email))
	if is_limited:
		return InvalidCouponResponse(valid=False, error=error)

	if coupon.coupon_type == "Discount":
		return DiscountCouponResponse(
			valid=True,
			coupon_type="Discount",
			discount_type=coupon.discount_type,
			discount_value=coupon.discount_value,
			max_discount_amount=coupon.maximum_discount_amount or 0,
			min_order_value=coupon.minimum_order_value or 0,
		)

	remaining = coupon.number_of_free_tickets - coupon.free_tickets_claimed
	if remaining <= 0:
		return InvalidCouponResponse(valid=False, error=_("All free tickets have been claimed"))

	return FreeTicketsCouponResponse(
		valid=True,
		coupon_type="Free Tickets",
		ticket_type=coupon.ticket_type,
		remaining_tickets=remaining,
		free_add_ons=[row.add_on for row in coupon.free_add_ons],
	)


def resolve_coupon_user(user_email: str | None) -> str | None:
	if frappe.session.user != "Guest":
		return frappe.session.user
	return user_email.lower().strip() if user_email else None
