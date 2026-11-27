import frappe
from frappe.utils import flt

from buzz.api.booking.exceptions import InvalidCoupon
from buzz.api.booking.schemas import DiscountQuote, DiscountQuoteRequest
from buzz.ticketing.doctype.buzz_coupon_code.buzz_coupon_code import BuzzCouponCode


def quote_discount(request: DiscountQuoteRequest) -> DiscountQuote:
	"""Price the cart through the same coupon rules a booking uses, without saving anything."""
	booking = build_cart(request)
	if not request.coupon_code:
		coupon = BuzzCouponCode.best_automatic(booking)
		return DiscountQuote(
			discount_amount=coupon.discount_for(booking) if coupon else 0,
			coupon_code=None,
			error=None,
			offer_name=coupon.code if coupon else None,
		)
	coupon = BuzzCouponCode.find_by_code(request.event, request.coupon_code)
	error = coupon.unusable_reason(booking) if coupon else str(InvalidCoupon.message)
	if error and coupon and coupon.coupon_type == "Access Code":
		# A specific reason would confirm the access code exists.
		error = str(InvalidCoupon.message)
	if error:
		return DiscountQuote(discount_amount=0, coupon_code=None, error=error)
	return quote_with_code(booking, coupon)


def quote_with_code(booking, coupon: BuzzCouponCode) -> DiscountQuote:
	"""An access code without a discount leaves the automatic offer in place."""
	if coupon.discount_type != "None":
		return DiscountQuote(
			discount_amount=coupon.discount_for(booking), coupon_code=coupon.code, error=None
		)
	offer = BuzzCouponCode.best_automatic(booking)
	return DiscountQuote(
		discount_amount=offer.discount_for(booking) if offer else 0,
		coupon_code=coupon.code,
		error=None,
		offer_name=offer.code if offer else None,
	)


def build_cart(request: DiscountQuoteRequest):
	booking = frappe.new_doc("Event Booking")
	booking.update(
		{
			"event": request.event,
			"currency": request.currency,
			"buyer_email": request.buyer_email,
			"user": frappe.session.user,
		}
	)
	cart = cart_lines(request)
	for ticket_type, _add_ons in cart:
		booking.append("attendees", {"ticket_type": ticket_type})
	booking.fetch_amounts_from_ticket_types()
	set_add_on_totals(booking, [add_ons for _ticket_type, add_ons in cart])
	return booking


def cart_lines(request: DiscountQuoteRequest) -> list[tuple[str, list[str]]]:
	"""Each allowed ticket with the add-ons picked for it."""
	allowed = set(event_ticket_types(request))
	add_ons = request.add_ons + [[]] * (len(request.ticket_types) - len(request.add_ons))
	return [line for line in zip(request.ticket_types, add_ons, strict=False) if line[0] in allowed]


def set_add_on_totals(booking, add_ons_per_attendee: list[list[str]]) -> None:
	"""Price each attendee's add-ons the way a booking would, from the event's enabled add-ons."""
	prices = add_on_prices(booking, {name for names in add_ons_per_attendee for name in names})
	for attendee, names in zip(booking.attendees, add_ons_per_attendee, strict=True):
		attendee.add_on_total = sum(
			price
			for scope, price in (prices[name] for name in names if name in prices)
			if not scope or attendee.ticket_type in scope
		)


def add_on_prices(booking, names: set[str]) -> dict[str, tuple[set[str], float]]:
	if not names:
		return {}
	filters = {
		"event": booking.event,
		"enabled": 1,
		"currency": booking.currency,
		"name": ["in", list(names)],
	}
	fields = ["name", "price", {"ticket_types": ["ticket_type"]}]
	rows = frappe.get_all("Ticket Add-on", filters=filters, fields=fields)
	return {row.name: ({str(link.ticket_type) for link in row.ticket_types}, flt(row.price)) for row in rows}


def event_ticket_types(request: DiscountQuoteRequest) -> list[str]:
	filters = {"event": request.event, "name": ["in", request.ticket_types], "is_published": 1}
	rows = frappe.get_all("Event Ticket Type", filters=filters, fields=["name", "is_hidden"])
	unlocked = unlocked_ticket_types(request)
	allowed = {str(row.name) for row in rows if not row.is_hidden or str(row.name) in unlocked}
	return [name for name in request.ticket_types if name in allowed]


def unlocked_ticket_types(request: DiscountQuoteRequest) -> set[str]:
	coupon = BuzzCouponCode.find_available_access_code(request.event, request.coupon_code)
	return coupon.unlocked_ticket_types() if coupon else set()
