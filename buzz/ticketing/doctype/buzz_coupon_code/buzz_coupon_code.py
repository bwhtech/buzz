# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import default_currency


class BuzzCouponCode(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.ticketing.doctype.coupon_free_add_on.coupon_free_add_on import CouponFreeAddon

		applies_to: DF.Literal["", "Event", "Event Category"]
		code: DF.Data | None
		coupon_type: DF.Literal["Free Tickets", "Discount"]
		discount_type: DF.Literal["Percentage", "Flat Amount"]
		discount_value: DF.Float
		event: DF.Link | None
		event_category: DF.Link | None
		free_add_ons: DF.Table[CouponFreeAddon]
		is_active: DF.Check
		max_usage_count: DF.Int
		max_usage_per_user: DF.Int
		maximum_discount_amount: DF.Float
		minimum_order_value: DF.Float
		number_of_free_tickets: DF.Int
		ticket_type: DF.Link | None
		valid_from: DF.Date | None
		valid_till: DF.Date | None
	# end: auto-generated types

	def autoname(self):
		if not self.code:
			self.code = frappe.generate_hash(length=8).upper()

	def validate(self):
		self.validate_discount_value()
		self.validate_scope()
		self.validate_free_tickets_event()
		self.validate_validity_dates()

	def validate_validity_dates(self):
		if self.valid_from and self.valid_till:
			if self.valid_from > self.valid_till:
				frappe.throw(_("Valid From cannot be after Valid Till"))

	def validate_discount_value(self):
		if self.coupon_type == "Discount":
			if self.discount_value <= 0:
				frappe.throw(_("Discount value must be greater than 0"))
			if self.discount_type == "Percentage" and self.discount_value > 100:
				frappe.throw(_("Percentage discount cannot exceed 100%"))

	def validate_scope(self):
		if self.applies_to == "Event":
			self.event_category = None
		elif self.applies_to == "Event Category":
			self.event = None
		else:
			self.event = None
			self.event_category = None

	def validate_free_tickets_event(self):
		if self.coupon_type == "Free Tickets":
			if self.applies_to != "Event":
				frappe.throw(_("Free Tickets coupon must be restricted to an Event"))
			if not self.event:
				frappe.throw(_("Event is required for Free Tickets coupon"))
			if not self.ticket_type:
				frappe.throw(_("Ticket Type is required for Free Tickets coupon"))
			if self.number_of_free_tickets <= 0:
				frappe.throw(_("Number of free tickets must be greater than 0"))

	def is_valid_for_event(self, event_name):
		if not self.is_active:
			return False, _("Coupon is not active")

		is_valid, msg = self.is_within_validity_period()
		if not is_valid:
			return False, msg

		if not self.applies_to:
			return True, ""

		if self.applies_to == "Event":
			if str(self.event) != str(event_name):
				return False, _("Coupon is not valid for this event")
			return True, ""

		if self.applies_to == "Event Category":
			event_category = frappe.get_cached_value("Buzz Event", event_name, "category")
			if not event_category or str(event_category) != str(self.event_category):
				return False, _("Coupon is not valid for this event category")
			return True, ""

	def is_usable_in_currency(self, currency: str | None, event: str):
		uses_fixed_amounts = self.coupon_type == "Discount" and (
			self.discount_type == "Flat Amount" or self.minimum_order_value or self.maximum_discount_amount
		)
		if currency and uses_fixed_amounts and currency != default_currency(event):
			return False, _("This coupon can't be used when paying in {0}").format(currency)
		return True, ""

	def is_usage_available(self):
		if self.max_usage_count > 0:
			if self.times_used >= self.max_usage_count:
				return False, _("Coupon usage limit reached")
		return True, ""

	def is_min_order_met(self, order_amount):
		if self.minimum_order_value > 0:
			if order_amount < self.minimum_order_value:
				gap = self.minimum_order_value - order_amount
				return False, _("Add {0} more to use this coupon (min order {1})").format(
					gap, self.minimum_order_value
				)
		return True, ""

	def is_within_validity_period(self):
		today = frappe.utils.getdate()

		if self.valid_from and today < frappe.utils.getdate(self.valid_from):
			return False, _("Coupon is not yet active (starts {0})").format(self.valid_from)

		if self.valid_till and today > frappe.utils.getdate(self.valid_till):
			return False, _("Coupon expired on {0}").format(self.valid_till)

		return True, ""

	def is_user_limit_reached(self, user=None):
		if not self.max_usage_per_user:
			return False, ""

		user = user or frappe.session.user
		user_usage = frappe.db.count(
			"Event Booking", {"coupon_code": self.name, "user": user, "docstatus": 1}
		)

		if user_usage >= self.max_usage_per_user:
			return True, _("You have reached the maximum usage limit for this coupon")

		return False, ""

	@property
	def times_used(self):
		return frappe.db.count("Event Booking", {"coupon_code": self.name, "docstatus": 1})

	@property
	def free_tickets_claimed(self):
		"""Calculate total attendees from all submitted bookings using this coupon"""
		from frappe.query_builder.functions import Count

		EventBooking = frappe.qb.DocType("Event Booking")
		EventBookingAttendee = frappe.qb.DocType("Event Booking Attendee")

		count = (
			frappe.qb.from_(EventBookingAttendee)
			.join(EventBooking)
			.on(EventBooking.name == EventBookingAttendee.parent)
			.where(EventBooking.coupon_code == self.name)
			.where(EventBooking.docstatus == 1)
			.where(EventBookingAttendee.ticket_type == self.ticket_type)
			.select(Count(EventBookingAttendee.name))
		).run()[0][0]

		return count or 0
