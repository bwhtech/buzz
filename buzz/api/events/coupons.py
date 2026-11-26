from collections import Counter

import frappe
from frappe.query_builder.functions import Count, Sum
from frappe.utils import flt, getdate

from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.events.schemas import CouponItem, CouponTicketType, CurrencyAmount, EventCoupons
from buzz.api.events.services import get_event_doc, registration_link
from buzz.permissions import event_section_permissions

COUPON_FIELDS = [
	"name",
	"coupon_type",
	"code",
	"description",
	"enabled",
	"discount_type",
	"discount_percentage",
	"applies_to_all_ticket_types",
	"minimum_requirement",
	"minimum_ticket_count",
	"usage_limit",
	"once_per_buyer",
	"starts_on",
	"expires_on",
	{"discount_amounts": ["currency", "price"]},
	{"minimum_order_amounts": ["currency", "price"]},
	{"ticket_types": ["ticket_type"]},
]


def event_coupons(event: str) -> EventCoupons:
	doc = get_event_doc(event)
	event_id = str(doc.name)
	perms = event_section_permissions(event_id, "ticketing", team=doc.team or "")
	if not perms["can_read"]:
		CannotManageEvent.throw()
	rows = coupon_rows(event_id)
	used, discounted = coupon_redemption_stats(event_id) if rows else (Counter(), [])
	return EventCoupons(
		title=doc.title,
		can_write=perms["can_write"],
		registration_link=registration_link(doc),
		coupons=[coupon_item(row, used.get(row.name, 0)) for row in rows],
		ticket_types=coupon_ticket_types(event_id),
		discounted=discounted,
	)


def coupon_rows(event: str) -> list[frappe._dict]:
	coupon = frappe.qb.DocType("Buzz Coupon Code")
	rows = (
		frappe.qb.from_(coupon)
		.select(
			coupon.name,
			coupon.coupon_type,
			coupon.code,
			coupon.description,
			coupon.enabled,
			coupon.discount_type,
			coupon.discount_percentage,
			coupon.applies_to_all_ticket_types,
			coupon.minimum_requirement,
			coupon.minimum_ticket_count,
			coupon.usage_limit,
			coupon.once_per_buyer,
			coupon.starts_on,
			coupon.expires_on,
		)
		.where(coupon.event == event)
		.orderby(coupon.creation, order=frappe.qb.desc)
	).run(as_dict=True)
	if not rows:
		return []
	names = [row.name for row in rows]
	price = frappe.qb.DocType("Buzz Price")
	price_rows = (
		frappe.qb.from_(price)
		.select(price.parent, price.parentfield, price.currency, price.price)
		.where(
			(price.parenttype == "Buzz Coupon Code")
			& price.parentfield.isin(["discount_amounts", "minimum_order_amounts"])
			& price.parent.isin(names)
		)
		.orderby(price.idx)
	).run(as_dict=True)
	discounts_by_parent: dict[str, list] = {}
	minimums_by_parent: dict[str, list] = {}
	for row in price_rows:
		entry = frappe._dict(currency=row.currency, price=row.price)
		target = discounts_by_parent if row.parentfield == "discount_amounts" else minimums_by_parent
		target.setdefault(row.parent, []).append(entry)

	scope = frappe.qb.DocType("Buzz Coupon Ticket Type")
	scope_rows = (
		frappe.qb.from_(scope)
		.select(scope.parent, scope.ticket_type)
		.where((scope.parenttype == "Buzz Coupon Code") & scope.parent.isin(names))
		.orderby(scope.idx)
	).run(as_dict=True)
	types_by_parent: dict[str, list] = {}
	for row in scope_rows:
		types_by_parent.setdefault(row.parent, []).append(row)

	for row in rows:
		row["discount_amounts"] = discounts_by_parent.get(row.name, [])
		row["minimum_order_amounts"] = minimums_by_parent.get(row.name, [])
		row["ticket_types"] = types_by_parent.get(row.name, [])
	return rows


def coupon_item(row, times_used: int) -> CouponItem:
	ticket_types = [str(link.ticket_type) for link in row.ticket_types]
	return CouponItem(
		**{
			**row,
			"ticket_types": ticket_types,
			"times_used": times_used,
			"status": status_of(row, times_used),
		}
	)


def status_of(row, times_used: int) -> str:
	if not row.enabled:
		return "Disabled"
	if row.usage_limit and times_used >= row.usage_limit:
		return "Used up"
	if row.expires_on and getdate() > getdate(row.expires_on):
		return "Ended"
	if row.starts_on and getdate() < getdate(row.starts_on):
		return "Scheduled"
	return "Active"


def coupon_ticket_types(event: str) -> list[CouponTicketType]:
	tt = frappe.qb.DocType("Event Ticket Type")
	rows = (
		frappe.qb.from_(tt)
		.select(tt.name, tt.title, tt.is_hidden)
		.where(tt.event == str(event))
		.orderby(tt.creation)
	).run(as_dict=True)
	if not rows:
		return []
	price = frappe.qb.DocType("Buzz Price")
	price_rows = (
		frappe.qb.from_(price)
		.select(price.parent, price.currency, price.price)
		.where(
			(price.parenttype == "Event Ticket Type")
			& (price.parentfield == "prices")
			& price.parent.isin([str(row.name) for row in rows])
		)
		.orderby(price.idx)
	).run(as_dict=True)
	prices_by_parent: dict[str, list] = {}
	for row in price_rows:
		prices_by_parent.setdefault(str(row.parent), []).append(
			frappe._dict(currency=row.currency, price=row.price)
		)
	return [
		CouponTicketType(**{**row, "name": str(row.name), "prices": prices_by_parent.get(str(row.name), [])})
		for row in rows
	]


def coupon_redemption_stats(event: str) -> tuple[Counter, list[CurrencyAmount]]:
	"""Usage counts per coupon/access code and discounted totals by currency, in one query."""
	booking = frappe.qb.DocType("Event Booking")
	rows = (
		frappe.qb.from_(booking)
		.select(
			booking.coupon_code,
			booking.access_code,
			booking.currency,
			Count(booking.name).as_("count"),
			Sum(booking.discount_amount).as_("discount"),
		)
		.where(
			(booking.event == str(event))
			& (booking.docstatus == 1)
			& (booking.coupon_code.isnotnull() | booking.access_code.isnotnull())
		)
		.groupby(booking.coupon_code, booking.access_code, booking.currency)
	).run(as_dict=True)

	used: Counter = Counter()
	discounted_totals: dict[str, float] = {}
	for row in rows:
		if row.access_code:
			used[row.access_code] += row.count
		if row.coupon_code:
			if row.coupon_code != row.access_code:
				used[row.coupon_code] += row.count
			discounted_totals[row.currency] = discounted_totals.get(row.currency, 0.0) + flt(row.discount)

	discounted = [
		CurrencyAmount(currency=currency, amount=discounted_totals[currency])
		for currency in sorted(discounted_totals, key=lambda key: key or "")
	]
	return used, discounted
