# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import re
from typing import TYPE_CHECKING

import frappe
from frappe import _, _lt
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Count
from frappe.utils import add_to_date, cint, cstr, flt, fmt_money, getdate, now_datetime

if TYPE_CHECKING:
	from buzz.ticketing.doctype.event_booking.event_booking import EventBooking


UNFINISHED_CHECKOUT_MESSAGE = _lt(
	"You have an unfinished checkout with this code. Try again in a few minutes."
)
PROMO_CODE_PATTERN = re.compile(r"[A-Z0-9_-]+")
TYPED_CODE_TYPES = ("Promo Code", "Access Code")


class BuzzCouponCode(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.buzz_price.buzz_price import BuzzPrice
		from buzz.ticketing.doctype.buzz_coupon_ticket_type.buzz_coupon_ticket_type import (
			BuzzCouponTicketType,
		)

		applies_to_all_ticket_types: DF.Check
		code: DF.Data | None
		coupon_type: DF.Literal["Promo Code", "Automatic", "Access Code"]
		description: DF.SmallText | None
		discount_amounts: DF.Table[BuzzPrice]
		discount_percentage: DF.Percent
		discount_type: DF.Literal["Percentage", "Flat Amount", "None"]
		enabled: DF.Check
		event: DF.Link
		expires_on: DF.Date | None
		minimum_order_amounts: DF.Table[BuzzPrice]
		minimum_requirement: DF.Literal["None", "Minimum Order Amount", "Minimum Ticket Count"]
		minimum_ticket_count: DF.Int
		once_per_buyer: DF.Check
		starts_on: DF.Date | None
		ticket_types: DF.TableMultiSelect[BuzzCouponTicketType]
		usage_limit: DF.Int
	# end: auto-generated types

	def validate(self):
		self.normalize_code()
		self.validate_unique_code()
		self.validate_discount()
		self.validate_ticket_types()
		self.validate_minimum()
		self.validate_schedule()

	def normalize_code(self):
		"""A promo or access code is typed at checkout; an automatic coupon's code is its offer name."""
		self.code = cstr(self.code).strip() or None
		if not self.code:
			frappe.throw(_("A coupon needs a code"))
		if self.coupon_type in TYPED_CODE_TYPES:
			self.code = self.code.upper()
			if not PROMO_CODE_PATTERN.fullmatch(self.code):
				frappe.throw(_("A promo code can only have letters, numbers, hyphens and underscores"))

	def validate_schedule(self):
		if self.starts_on and self.expires_on and getdate(self.starts_on) > getdate(self.expires_on):
			frappe.throw(_("The coupon can't start after it expires"))

	def validate_unique_code(self):
		filters = {"event": self.event, "code": self.code, "name": ["!=", self.name]}
		if self.code and frappe.db.exists("Buzz Coupon Code", filters):
			frappe.throw(_("Code {0} is already used on this event").format(self.code))

	def validate_discount(self):
		if self.discount_type == "None":
			if self.coupon_type != "Access Code":
				frappe.throw(_("Only an access code can have no discount"))
		elif self.discount_type == "Flat Amount":
			validate_amount_rows(self.discount_amounts, _("Discount Amounts"))
		elif not 0 < flt(self.discount_percentage) <= 100:
			frappe.throw(_("Discount Percentage must be more than 0 and at most 100"))

	def validate_ticket_types(self):
		if self.coupon_type == "Access Code":
			self.applies_to_all_ticket_types = 0
		if self.applies_to_all_ticket_types:
			self.ticket_types = []
			return
		if not self.ticket_types:
			frappe.throw(_("Select the ticket types this coupon applies to"))
		names = [row.ticket_type for row in self.ticket_types]
		events = frappe.get_all("Event Ticket Type", filters={"name": ["in", names]}, pluck="event")
		if any(str(event) != str(self.event) for event in events):
			frappe.throw(_("Ticket types must belong to the coupon's event"))
		if self.coupon_type == "Access Code":
			self.validate_scope_is_hidden(names)

	def validate_scope_is_hidden(self, names: list):
		filters = {"name": ["in", names], "is_hidden": 0}
		if frappe.db.exists("Event Ticket Type", filters):
			frappe.throw(_("An access code can only unlock hidden ticket types"))

	def validate_minimum(self):
		if self.minimum_requirement == "Minimum Order Amount":
			validate_amount_rows(self.minimum_order_amounts, _("Minimum Order Amounts"))
		elif self.minimum_requirement == "Minimum Ticket Count" and cint(self.minimum_ticket_count) <= 0:
			frappe.throw(_("Minimum Ticket Count must be more than 0"))

	@classmethod
	def find_by_code(cls, event: str, code: str | None) -> "BuzzCouponCode | None":
		filters = {
			"event": event,
			"coupon_type": ["in", TYPED_CODE_TYPES],
			"code": cstr(code).strip().upper(),
		}
		name = frappe.db.get_value("Buzz Coupon Code", filters)
		return frappe.get_cached_doc("Buzz Coupon Code", name) if name else None

	@classmethod
	def find_available_access_code(cls, event: str, code: str | None) -> "BuzzCouponCode | None":
		"""The access code typed for the event, if it is open and not used up."""
		coupon = cls.find_by_code(event, code) if code else None
		if coupon and coupon.coupon_type == "Access Code" and coupon.is_available(event):
			return coupon

	@classmethod
	def best_automatic(cls, booking: "EventBooking", use_cache: bool = True) -> "BuzzCouponCode | None":
		coupon_table = frappe.qb.DocType("Buzz Coupon Code")
		names = (
			frappe.qb.from_(coupon_table)
			.select(coupon_table.name)
			.where(
				(coupon_table.event == str(booking.event))
				& (coupon_table.coupon_type == "Automatic")
				& (coupon_table.enabled == 1)
			)
			.orderby(coupon_table.creation)
		).run(pluck=True)
		if not names:
			return None
		loader = frappe.get_cached_doc if use_cache else frappe.get_doc
		coupons = [loader("Buzz Coupon Code", name) for name in names]
		open_coupons = [coupon for coupon in coupons if coupon.is_open(booking.event)]
		limited_names = [coupon.name for coupon in open_coupons if coupon.usage_limit]
		taken_map = cls.batch_times_taken(limited_names, booking) if limited_names else {}
		usable = [
			coupon
			for coupon in open_coupons
			if coupon.unusable_reason(booking, taken_override=taken_map.get(coupon.name)) is None
		]
		best = max(usable, key=lambda coupon: coupon.discount_for(booking), default=None)
		return best if best and best.discount_for(booking) > 0 else None

	@classmethod
	def batch_times_taken(cls, coupon_names: list[str], booking: "EventBooking") -> dict[str, int]:
		"""Taken counts for multiple automatic/promo coupons in a single grouped query."""
		from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD
		from buzz.ticketing.doctype.ticket_hold.ticket_hold import PAYMENT_HOLD_MINUTES

		table = frappe.qb.DocType("Event Booking")
		window_start = add_to_date(now_datetime(), minutes=-PAYMENT_HOLD_MINUTES)
		live_draft = (
			(table.docstatus == 0)
			& ((table.payment_method == OFFLINE_PAYMENT_METHOD) | (table.creation > window_start))
			& table.buyer_email.isnotnull()
		)
		rows = (
			frappe.qb.from_(table)
			.select(table.coupon_code, Count(table.name))
			.where(table.coupon_code.isin(coupon_names))
			.where(table.name != cstr(booking.name))
			.where((table.docstatus == 1) | live_draft)
			.groupby(table.coupon_code)
		).run()
		counts = {name: 0 for name in coupon_names}
		for code, count in rows:
			counts[code] = count
		return counts

	@classmethod
	def lock_for(cls, booking: "EventBooking") -> None:
		"""Lock the limited coupons the booking can use, in name order, so bookings check usage
		limits one at a time until the transaction ends."""
		coupon = frappe.qb.DocType("Buzz Coupon Code")
		candidates = {name for name in (booking.coupon_code, booking.access_code) if name}
		if not booking.coupon_code:
			auto_names = (
				frappe.qb.from_(coupon)
				.select(coupon.name)
				.where(
					(coupon.event == str(booking.event))
					& (coupon.coupon_type == "Automatic")
					& ((coupon.usage_limit > 0) | (coupon.once_per_buyer == 1))
				)
			).run(pluck=True)
			candidates.update(auto_names)
		if not candidates:
			return
		(
			frappe.qb.from_(coupon)
			.select(coupon.name)
			.where(coupon.name.isin(sorted(candidates)))
			.where((coupon.usage_limit > 0) | (coupon.once_per_buyer == 1))
			.orderby(coupon.name)
			.for_update()
		).run()

	def is_open(self, event: str) -> bool:
		started = not self.starts_on or getdate() >= getdate(self.starts_on)
		expired = self.expires_on and getdate() > getdate(self.expires_on)
		return bool(self.enabled) and started and not expired and str(self.event) == str(event)

	def is_available(self, event: str) -> bool:
		within_limit = not self.usage_limit or self.times_used() < self.usage_limit
		return self.is_open(event) and within_limit

	def unusable_reason(self, booking: "EventBooking", taken_override: int | None = None) -> str | None:
		from buzz.api.booking.exceptions import InvalidCoupon

		if not self.is_open(booking.event):
			return str(InvalidCoupon.message)
		return self.limit_reason(booking, taken_override=taken_override) or self.eligibility_reason(booking)

	def limit_reason(self, booking: "EventBooking", taken_override: int | None = None) -> str | None:
		return self.usage_limit_reason(booking, taken_override=taken_override) or self.once_per_buyer_reason(
			booking
		)

	def usage_limit_reason(self, booking: "EventBooking", taken_override: int | None = None) -> str | None:
		if not self.usage_limit:
			return None
		taken = self.times_taken(booking) if taken_override is None else taken_override
		if taken < self.usage_limit:
			return None
		if taken - self.own_live_drafts(booking) < self.usage_limit:
			return str(UNFINISHED_CHECKOUT_MESSAGE)
		return _("This coupon has reached its usage limit")

	def once_per_buyer_reason(self, booking: "EventBooking") -> str | None:
		if not self.once_per_buyer:
			return None
		if self.times_used_by(booking):
			return _("You have already used this coupon")
		if self.own_live_drafts(booking):
			return str(UNFINISHED_CHECKOUT_MESSAGE)

	def eligibility_reason(self, booking: "EventBooking") -> str | None:
		# An access code is applied before its hidden tickets are in the cart.
		if not self.eligible_attendees(booking) and self.coupon_type != "Access Code":
			return _("This coupon doesn't apply to the selected tickets")
		uses_amounts = self.discount_type == "Flat Amount"
		if uses_amounts and amount_in(self.discount_amounts, booking.currency) is None:
			return currency_message(booking.currency)
		return self.minimum_reason(booking)

	def minimum_reason(self, booking: "EventBooking") -> str | None:
		if self.minimum_requirement == "Minimum Ticket Count":
			if len(self.eligible_attendees(booking)) < self.minimum_ticket_count:
				return _("Add at least {0} eligible tickets to use this coupon").format(
					self.minimum_ticket_count
				)
		if self.minimum_requirement == "Minimum Order Amount":
			minimum = amount_in(self.minimum_order_amounts, booking.currency)
			if minimum is None:
				return currency_message(booking.currency)
			if self.eligible_subtotal(booking) < minimum:
				return _("Spend at least {0} on eligible tickets to use this coupon").format(
					fmt_money(minimum, currency=booking.currency)
				)

	def discount_for(self, booking: "EventBooking") -> float:
		if self.discount_type == "None":
			return 0
		subtotal = self.eligible_subtotal(booking)
		if self.discount_type == "Percentage":
			return flt(subtotal * flt(self.discount_percentage) / 100, 2)
		return min(amount_in(self.discount_amounts, booking.currency) or 0, subtotal)

	def unlocked_ticket_types(self) -> set[str]:
		if self.coupon_type != "Access Code":
			return set()
		return {str(row.ticket_type) for row in self.ticket_types}

	@property
	def usage_field(self) -> str:
		"""The Event Booking field that records a use of this coupon."""
		return "access_code" if self.coupon_type == "Access Code" else "coupon_code"

	def eligible_attendees(self, booking: "EventBooking") -> list:
		if self.applies_to_all_ticket_types:
			return list(booking.attendees)
		scope = {str(row.ticket_type) for row in self.ticket_types}
		return [attendee for attendee in booking.attendees if str(attendee.ticket_type) in scope]

	def eligible_subtotal(self, booking: "EventBooking") -> float:
		return sum(flt(attendee.amount) for attendee in self.eligible_attendees(booking))

	def times_used(self, exclude: str | None = None) -> int:
		return frappe.db.count("Event Booking", self.usage_filters(exclude))

	def times_used_by(self, booking: "EventBooking") -> int:
		submitted = frappe.qb.DocType("Event Booking")
		used = (
			frappe.qb.from_(submitted)
			.select(Count(submitted.name))
			.where((submitted.coupon_code == self.name) & (submitted.docstatus == 1))
			.where(submitted.name != cstr(booking.name))
		)
		return count_for_buyer(used, booking)

	def own_live_drafts(self, booking: "EventBooking") -> int:
		return count_for_buyer(self.live_drafts(booking), booking)

	def times_taken(self, booking: "EventBooking") -> int:
		from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD
		from buzz.ticketing.doctype.ticket_hold.ticket_hold import PAYMENT_HOLD_MINUTES

		table = frappe.qb.DocType("Event Booking")
		window_start = add_to_date(now_datetime(), minutes=-PAYMENT_HOLD_MINUTES)
		live_draft = (
			(table.docstatus == 0)
			& ((table.payment_method == OFFLINE_PAYMENT_METHOD) | (table.creation > window_start))
			& table.buyer_email.isnotnull()
		)
		return (
			frappe.qb.from_(table)
			.select(Count(table.name))
			.where(getattr(table, self.usage_field) == self.name)
			.where(table.name != cstr(booking.name))
			.where((table.docstatus == 1) | live_draft)
		).run()[0][0]

	def live_drafts(self, booking: "EventBooking"):
		"""Drafts still being paid for: online ones for the payment window, offline ones until
		approved or rejected."""
		from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD
		from buzz.ticketing.doctype.ticket_hold.ticket_hold import PAYMENT_HOLD_MINUTES

		draft = frappe.qb.DocType("Event Booking")
		window_start = add_to_date(now_datetime(), minutes=-PAYMENT_HOLD_MINUTES)
		return (
			frappe.qb.from_(draft)
			.select(Count(draft.name))
			.where((getattr(draft, self.usage_field) == self.name) & (draft.docstatus == 0))
			.where(draft.name != cstr(booking.name))
			.where((draft.payment_method == OFFLINE_PAYMENT_METHOD) | (draft.creation > window_start))
			.where(draft.buyer_email.isnotnull())
		)

	def usage_filters(self, exclude: str | None) -> dict:
		filters = {self.usage_field: self.name, "docstatus": 1}
		if exclude:
			filters["name"] = ["!=", exclude]
		return filters


def on_doctype_update():
	# validate_unique_code names the clash; the index stops two concurrent inserts.
	frappe.db.add_unique("Buzz Coupon Code", ["event", "code"])


def count_for_buyer(query, booking: "EventBooking") -> int:
	"""Count the query's bookings of the same buyer, matched by email, and by user when logged in."""
	table = frappe.qb.DocType("Event Booking")
	conditions = []
	if booking.buyer_email:
		conditions.append(table.buyer_email == booking.buyer_email.strip().lower())
	if booking.user and booking.user != "Guest":
		conditions.append(table.user == booking.user)
	return query.where(Criterion.any(conditions)).run()[0][0] if conditions else 0


def validate_amount_rows(rows: list, label: str):
	currencies = [row.currency for row in rows]
	if not rows:
		frappe.throw(_("{0} needs at least one row").format(label))
	if any(flt(row.price) <= 0 for row in rows):
		frappe.throw(_("{0} must be more than 0").format(label))
	if len(set(currencies)) != len(currencies):
		frappe.throw(_("{0} can have only one row per currency").format(label))


def amount_in(rows: list, currency: str | None) -> float | None:
	return next((flt(row.price) for row in rows if row.currency == currency), None)


def currency_message(currency: str | None) -> str:
	return _("This coupon can't be used when paying in {0}").format(currency)
