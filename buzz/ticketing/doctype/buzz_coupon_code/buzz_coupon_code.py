# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from frappe.utils import add_to_date, cint, cstr, flt, fmt_money, getdate, now_datetime

if TYPE_CHECKING:
	from buzz.ticketing.doctype.event_booking.event_booking import EventBooking


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
		coupon_type: DF.Literal["Promo Code", "Automatic"]
		description: DF.SmallText | None
		discount_amounts: DF.Table[BuzzPrice]
		discount_percentage: DF.Percent
		discount_type: DF.Literal["Percentage", "Flat Amount"]
		enabled: DF.Check
		event: DF.Link
		expires_on: DF.Date | None
		minimum_order_amounts: DF.Table[BuzzPrice]
		minimum_requirement: DF.Literal["None", "Minimum Order Amount", "Minimum Ticket Count"]
		minimum_ticket_count: DF.Int
		once_per_buyer: DF.Check
		ticket_types: DF.TableMultiSelect[BuzzCouponTicketType]
		usage_limit: DF.Int
	# end: auto-generated types

	def validate(self):
		self.normalize_code()
		self.validate_unique_code()
		self.validate_discount()
		self.validate_ticket_types()
		self.validate_minimum()

	def normalize_code(self):
		self.code = cstr(self.code).strip().upper() or None
		if self.coupon_type == "Automatic":
			self.code = None
		elif not self.code:
			frappe.throw(_("A promo code needs a code"))

	def validate_unique_code(self):
		filters = {"event": self.event, "code": self.code, "name": ["!=", self.name]}
		if self.code and frappe.db.exists("Buzz Coupon Code", filters):
			frappe.throw(_("Code {0} is already used on this event").format(self.code))

	def validate_discount(self):
		if self.discount_type == "Flat Amount":
			validate_amount_rows(self.discount_amounts, _("Discount Amounts"))
		elif not 0 < flt(self.discount_percentage) <= 100:
			frappe.throw(_("Discount Percentage must be more than 0 and at most 100"))

	def validate_ticket_types(self):
		if self.applies_to_all_ticket_types:
			self.ticket_types = []
			return
		if not self.ticket_types:
			frappe.throw(_("Select the ticket types this coupon applies to"))
		names = [row.ticket_type for row in self.ticket_types]
		events = frappe.get_all("Event Ticket Type", filters={"name": ["in", names]}, pluck="event")
		if any(str(event) != str(self.event) for event in events):
			frappe.throw(_("Ticket types must belong to the coupon's event"))

	def validate_minimum(self):
		if self.minimum_requirement == "Minimum Order Amount":
			validate_amount_rows(self.minimum_order_amounts, _("Minimum Order Amounts"))
		elif self.minimum_requirement == "Minimum Ticket Count" and cint(self.minimum_ticket_count) <= 0:
			frappe.throw(_("Minimum Ticket Count must be more than 0"))

	@classmethod
	def find_promo(cls, event: str, code: str | None) -> "BuzzCouponCode | None":
		filters = {"event": event, "coupon_type": "Promo Code", "code": cstr(code).strip().upper()}
		name = frappe.db.get_value("Buzz Coupon Code", filters)
		return frappe.get_doc("Buzz Coupon Code", name) if name else None

	@classmethod
	def best_automatic(cls, booking: "EventBooking") -> "BuzzCouponCode | None":
		filters = {"event": booking.event, "coupon_type": "Automatic", "enabled": 1}
		names = frappe.get_all("Buzz Coupon Code", filters=filters, order_by="creation asc", pluck="name")
		coupons = [frappe.get_doc("Buzz Coupon Code", name) for name in names]
		usable = [coupon for coupon in coupons if coupon.unusable_reason(booking) is None]
		best = max(usable, key=lambda coupon: coupon.discount_for(booking), default=None)
		return best if best and best.discount_for(booking) > 0 else None

	@classmethod
	def lock_for(cls, booking: "EventBooking") -> None:
		"""Lock the limited coupons the booking can use, in name order, so bookings check usage
		limits one at a time until the transaction ends."""
		coupon = frappe.qb.DocType("Buzz Coupon Code")
		query = (
			frappe.qb.from_(coupon)
			.select(coupon.name)
			.where(coupon.usage_limit > 0)
			.orderby(coupon.name)
			.for_update()
		)
		if booking.coupon_code:
			query = query.where(coupon.name == booking.coupon_code)
		else:
			query = query.where((coupon.event == booking.event) & (coupon.coupon_type == "Automatic"))
		query.run()

	def is_open(self, event: str) -> bool:
		expired = self.expires_on and getdate() > getdate(self.expires_on)
		return bool(self.enabled) and not expired and str(self.event) == str(event)

	def unusable_reason(self, booking: "EventBooking") -> str | None:
		from buzz.api.booking.exceptions import InvalidCoupon

		if not self.is_open(booking.event):
			return str(InvalidCoupon.message)
		return self.limit_reason(booking) or self.eligibility_reason(booking)

	def limit_reason(self, booking: "EventBooking") -> str | None:
		if self.usage_limit and self.times_taken(booking) >= self.usage_limit:
			return _("This coupon has reached its usage limit")
		if self.once_per_buyer and self.times_used_by(booking.buyer_email, exclude=booking.name):
			return _("You have already used this coupon")

	def eligibility_reason(self, booking: "EventBooking") -> str | None:
		if not self.eligible_attendees(booking):
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
		subtotal = self.eligible_subtotal(booking)
		if self.discount_type == "Percentage":
			return flt(subtotal * flt(self.discount_percentage) / 100, 2)
		return min(amount_in(self.discount_amounts, booking.currency) or 0, subtotal)

	def eligible_attendees(self, booking: "EventBooking") -> list:
		if self.applies_to_all_ticket_types:
			return list(booking.attendees)
		scope = {str(row.ticket_type) for row in self.ticket_types}
		return [attendee for attendee in booking.attendees if str(attendee.ticket_type) in scope]

	def eligible_subtotal(self, booking: "EventBooking") -> float:
		return sum(flt(attendee.amount) for attendee in self.eligible_attendees(booking))

	def times_used(self, exclude: str | None = None) -> int:
		return frappe.db.count("Event Booking", self.usage_filters(exclude))

	def times_used_by(self, buyer_email: str | None, exclude: str | None = None) -> int:
		if not buyer_email:
			return 0
		filters = {**self.usage_filters(exclude), "buyer_email": buyer_email.strip().lower()}
		return frappe.db.count("Event Booking", filters)

	def times_taken(self, booking: "EventBooking") -> int:
		return self.times_used(exclude=booking.name) + self.times_reserved(booking)

	def times_reserved(self, booking: "EventBooking") -> int:
		"""Drafts other buyers are still paying for: online ones for the payment window,
		offline ones until approved or rejected."""
		from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD
		from buzz.ticketing.doctype.ticket_hold.ticket_hold import PAYMENT_HOLD_MINUTES

		draft = frappe.qb.DocType("Event Booking")
		window_start = add_to_date(now_datetime(), minutes=-PAYMENT_HOLD_MINUTES)
		query = (
			frappe.qb.from_(draft)
			.select(Count(draft.name))
			.where((draft.coupon_code == self.name) & (draft.docstatus == 0))
			.where(draft.name != cstr(booking.name))
			.where((draft.payment_method == OFFLINE_PAYMENT_METHOD) | (draft.creation > window_start))
			.where(draft.buyer_email.isnotnull())
		)
		if booking.buyer_email:
			query = query.where(draft.buyer_email != booking.buyer_email.strip().lower())
		return query.run()[0][0]

	def usage_filters(self, exclude: str | None) -> dict:
		filters = {"coupon_code": self.name, "docstatus": 1}
		if exclude:
			filters["name"] = ["!=", exclude]
		return filters


def on_doctype_update():
	# validate_unique_code names the clash; the index stops two concurrent inserts.
	frappe.db.add_unique("Buzz Coupon Code", ["event", "code"])


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
