import frappe
from frappe.query_builder.functions import Count, Sum
from frappe.utils import getdate

from buzz.api.events.schemas import CouponItem, CouponTicketType, CurrencyAmount, EventCoupons
from buzz.api.events.services import ensure_event_team_access, registration_link
from buzz.permissions import has_section_permission

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
	ensure_event_team_access(event, "ticketing")
	doc = frappe.get_cached_doc("Buzz Event", event)
	rows = frappe.get_all(
		"Buzz Coupon Code",
		filters={"event": event},
		fields=COUPON_FIELDS,
		order_by="creation desc",
		ignore_permissions=True,
	)
	used = times_used_by_coupon(event)
	return EventCoupons(
		title=doc.title,
		can_write=has_section_permission(event, "ticketing", "write", frappe.session.user),
		registration_link=registration_link(doc),
		coupons=[coupon_item(row, used.get(row.name, 0)) for row in rows],
		ticket_types=coupon_ticket_types(event),
		discounted=discounted_by_currency(event),
	)


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
	rows = frappe.get_all(
		"Event Ticket Type",
		filters={"event": event},
		fields=["name", "title", {"prices": ["currency", "price"]}],
		order_by="creation asc",
		ignore_permissions=True,
	)
	return [CouponTicketType(**{**row, "name": str(row.name)}) for row in rows]


def redeemed_bookings(event: str):
	booking = frappe.qb.DocType("Event Booking")
	query = frappe.qb.from_(booking).where(
		(booking.event == event) & (booking.docstatus == 1) & booking.coupon_code.isnotnull()
	)
	return booking, query


def times_used_by_coupon(event: str) -> dict[str, int]:
	booking, query = redeemed_bookings(event)
	rows = query.select(booking.coupon_code, Count(booking.name)).groupby(booking.coupon_code).run()
	return dict(rows)


def discounted_by_currency(event: str) -> list[CurrencyAmount]:
	booking, query = redeemed_bookings(event)
	rows = query.select(booking.currency, Sum(booking.discount_amount)).groupby(booking.currency).run()
	return [CurrencyAmount(currency=currency, amount=amount) for currency, amount in rows]
