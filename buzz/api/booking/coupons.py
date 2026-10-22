import frappe

from buzz.api.booking.exceptions import InvalidCoupon
from buzz.api.booking.schemas import DiscountQuote, DiscountQuoteRequest
from buzz.ticketing.doctype.buzz_coupon_code.buzz_coupon_code import BuzzCouponCode


def quote_discount(request: DiscountQuoteRequest) -> DiscountQuote:
	"""Price the cart through the same coupon rules a booking uses, without saving anything."""
	booking = build_cart(request)
	if not request.coupon_code:
		coupon = BuzzCouponCode.best_automatic(booking)
		return DiscountQuote(
			discount_amount=coupon.discount_for(booking) if coupon else 0, coupon_code=None, error=None
		)
	coupon = BuzzCouponCode.find_promo(request.event, request.coupon_code)
	error = coupon.unusable_reason(booking) if coupon else str(InvalidCoupon.message)
	if error:
		return DiscountQuote(discount_amount=0, coupon_code=None, error=error)
	return DiscountQuote(discount_amount=coupon.discount_for(booking), coupon_code=coupon.code, error=None)


def build_cart(request: DiscountQuoteRequest):
	booking = frappe.new_doc("Event Booking")
	booking.update({"event": request.event, "currency": request.currency, "buyer_email": request.buyer_email})
	for ticket_type in event_ticket_types(request):
		booking.append("attendees", {"ticket_type": ticket_type})
	booking.fetch_amounts_from_ticket_types()
	return booking


def event_ticket_types(request: DiscountQuoteRequest) -> list[str]:
	filters = {"event": request.event, "name": ["in", request.ticket_types]}
	allowed = {str(name) for name in frappe.get_all("Event Ticket Type", filters=filters, pluck="name")}
	return [name for name in request.ticket_types if name in allowed]
