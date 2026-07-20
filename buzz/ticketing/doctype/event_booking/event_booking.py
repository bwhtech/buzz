# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt
import json

import frappe
from frappe import _
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.model.document import Document

from buzz.api import OFFLINE_PAYMENT_METHOD
from buzz.payments import mark_payment_as_received


class EventBooking(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.utm_parameter.utm_parameter import UTMParameter
		from buzz.ticketing.doctype.additional_field.additional_field import AdditionalField
		from buzz.ticketing.doctype.event_booking_attendee.event_booking_attendee import EventBookingAttendee

		additional_fields: DF.Table[AdditionalField]
		amended_from: DF.Link | None
		attendees: DF.Table[EventBookingAttendee]
		billing_address: DF.SmallText | None
		coupon_code: DF.Link | None
		currency: DF.Link
		discount_amount: DF.Currency
		event: DF.Link
		invoice_requested: DF.Check
		naming_series: DF.Literal["B.###"]
		net_amount: DF.Currency
		offline_payment_method: DF.Data | None
		payment_method: DF.Data | None
		payment_status: DF.Literal["Unpaid", "Paid", "Verification Pending"]
		status: DF.Literal["Confirmed", "Approval Pending", "Approved", "Rejected"]
		tax_amount: DF.Currency
		tax_id: DF.Data | None
		tax_label: DF.Data | None
		tax_percentage: DF.Percent
		total_amount: DF.Currency
		user: DF.Link
		utm_parameters: DF.Table[UTMParameter]
	# end: auto-generated types

	def validate(self):
		self.validate_ticket_availability()
		self.fetch_amounts_from_ticket_types()
		self.set_currency()
		self.set_total()
		self.apply_coupon_if_applicable()
		self.apply_taxes_if_applicable()

	def before_submit(self):
		"""Set status before submit based on payment method."""
		# Skip if already approved (submission triggered by approve_booking)
		if self.status == "Approved":
			return

		if self.total_amount == 0:
			self.payment_status = "Paid"
			self.status = "Confirmed"
			return

		if self.payment_method == OFFLINE_PAYMENT_METHOD:
			frappe.throw(
				_(
					"This booking requires offline payment verification. Please use the Approve or Reject button instead."
				)
			)
		elif self.payment_status != "Paid":
			self.payment_status = "Unpaid"
			self.status = "Approval Pending"

	def set_currency(self):
		self.currency = self.attendees[0].currency

	def set_total(self):
		self.net_amount = 0
		for attendee in self.attendees:
			self.net_amount += attendee.amount
			if attendee.add_ons:
				attendee.add_on_total = attendee.get_add_on_total()
				attendee.number_of_add_ons = attendee.get_number_of_add_ons()
				self.net_amount += attendee.add_on_total
		self.total_amount = self.net_amount

	def apply_taxes_if_applicable(self):
		"""Apply tax based on event-level tax configuration."""
		self.tax_percentage = 0
		self.tax_amount = 0
		self.tax_label = None

		event = frappe.get_cached_doc("Buzz Event", self.event)
		if not event.apply_tax:
			return

		self.tax_label = event.tax_label or "Tax"
		self.tax_percentage = event.tax_percentage or 0

		if self.tax_percentage > 0:
			if event.tax_inclusive:
				# Tax is included in the price — back-calculate the tax component
				self.tax_amount = round(
					self.total_amount * self.tax_percentage / (100 + self.tax_percentage), 2
				)
			else:
				# Tax is added on top of the price
				self.tax_amount = self.total_amount * (self.tax_percentage / 100)
				self.total_amount += self.tax_amount

	def validate_ticket_availability(self):
		num_tickets_by_type = {}
		for attendee in self.attendees:
			if attendee.ticket_type not in num_tickets_by_type:
				num_tickets_by_type[attendee.ticket_type] = 0
			num_tickets_by_type[attendee.ticket_type] += 1

		for ticket_type, num_tickets in num_tickets_by_type.items():
			ticket_type_doc = frappe.get_cached_doc("Event Ticket Type", ticket_type)
			if not ticket_type_doc.is_published:
				frappe.throw(frappe._(f"{ticket_type_doc.title} tickets no longer available!"))

			if not ticket_type_doc.are_tickets_available(num_tickets):
				frappe.throw(
					frappe._(
						f"Only {ticket_type_doc.remaining_tickets} tickets available for {ticket_type_doc.title}, you are trying to book {num_tickets}!"
					)
				)

	def fetch_amounts_from_ticket_types(self):
		for attendee in self.attendees:
			price, currency = frappe.get_cached_value(
				"Event Ticket Type", attendee.ticket_type, ["price", "currency"]
			)
			# Always set price from ticket type - coupon will discount later
			attendee.amount = price
			if not attendee.currency:
				attendee.currency = currency

	def on_submit(self):
		self.validate_coupon_availability()
		self.generate_tickets()

		try:
			self.send_booking_confirmation_email()
		except Exception:
			frappe.log_error(
				title="Booking confirmation email failed",
				reference_doctype=self.doctype,
				reference_name=self.name,
			)

	def send_booking_confirmation_email(self):
		# Never email system/placeholder users — they are not real recipients.
		if self.user in ("Administrator", "Guest"):
			return

		event_doc = frappe.get_cached_doc("Buzz Event", self.event)
		if not event_doc.send_booking_confirmation_email:
			return

		recipient = frappe.db.get_value("User", self.user, "email") or self.user
		if not recipient:
			return

		# Fallback to global setting if event-level not set
		booking_template = event_doc.booking_confirmation_email_template or frappe.db.get_single_value(
			"Buzz Settings", "default_booking_confirmation_email_template"
		)

		subject = _("Your booking for {0} is confirmed ✅").format(event_doc.title)

		# Pre-fetch ticket type titles in a single query so the email template
		# loop stays a pure display operation (no per-attendee DB round-trips).
		ticket_type_names = list({attendee.ticket_type for attendee in self.attendees})
		ticket_type_titles = {}
		if ticket_type_names:
			ticket_type_titles = {
				row.name: row.title
				for row in frappe.get_all(
					"Event Ticket Type",
					filters={"name": ["in", ticket_type_names]},
					fields=["name", "title"],
				)
			}

		attendee_rows = [
			{
				"full_name": attendee.full_name
				or " ".join(part for part in (attendee.first_name, attendee.last_name) if part),
				"ticket_type_title": ticket_type_titles.get(attendee.ticket_type, attendee.ticket_type),
				"number_of_add_ons": attendee.number_of_add_ons,
				"amount": (attendee.amount or 0) + (attendee.add_on_total or 0),
			}
			for attendee in self.attendees
		]

		args = {
			"doc": self,
			"event_doc": event_doc,
			"event_title": event_doc.title,
			"venue": event_doc.venue,
			"attendee_rows": attendee_rows,
			"support_email": frappe.db.get_single_value("Buzz Settings", "support_email"),
		}

		content = None
		if booking_template:
			email_template = get_email_template(booking_template, args)
			subject = email_template.get("subject") or subject
			content = email_template.get("message")

		frappe.sendmail(
			recipients=[recipient],
			subject=subject,
			content=content,
			template=None if booking_template else "booking_confirmation",
			args=args,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

	def validate_coupon_availability(self):
		"""Re-validate coupon with lock to prevent race condition."""
		if not self.coupon_code:
			return

		# Lock coupon row to prevent concurrent over-allocation
		coupon = frappe.get_doc("Buzz Coupon Code", self.coupon_code, for_update=True)

		if coupon.coupon_type == "Free Tickets":
			# Count claimed tickets excluding current booking (since it's already docstatus=1 during on_submit)
			claimed = self.get_free_tickets_claimed_excluding_self(coupon)
			remaining = coupon.number_of_free_tickets - claimed

			# Count only attendees that were actually discounted (amount == 0)
			# This supports partial allocation where user books more tickets than remaining free
			coupon_ticket_type = str(coupon.ticket_type) if coupon.ticket_type else ""
			tickets_discounted = len(
				[a for a in self.attendees if str(a.ticket_type) == coupon_ticket_type and a.amount == 0]
			)

			if remaining < tickets_discounted:
				frappe.throw(_("Only {0} free tickets remaining").format(remaining))

	def get_free_tickets_claimed_excluding_self(self, coupon):
		"""Get free tickets claimed excluding current booking."""
		from frappe.query_builder.functions import Count

		EventBooking = frappe.qb.DocType("Event Booking")
		EventBookingAttendee = frappe.qb.DocType("Event Booking Attendee")

		count = (
			frappe.qb.from_(EventBookingAttendee)
			.join(EventBooking)
			.on(EventBooking.name == EventBookingAttendee.parent)
			.where(EventBooking.coupon_code == coupon.name)
			.where(EventBooking.docstatus == 1)
			.where(EventBooking.name != self.name)
			.where(EventBookingAttendee.ticket_type == coupon.ticket_type)
			.select(Count(EventBookingAttendee.name))
		).run()[0][0]

		return count or 0

	def generate_tickets(self):
		for attendee in self.attendees:
			ticket = frappe.new_doc("Event Ticket")
			ticket.event = self.event
			ticket.booking = self.name
			ticket.ticket_type = attendee.ticket_type
			ticket.first_name = attendee.first_name
			ticket.last_name = attendee.last_name
			ticket.attendee_email = attendee.email

			if attendee.add_ons:
				add_ons_list = frappe.get_cached_doc("Attendee Ticket Add-on", attendee.add_ons).add_ons
				ticket.add_ons = add_ons_list

			# Add custom fields from attendee to ticket
			if attendee.custom_fields:
				custom_fields_data = attendee.custom_fields
				if isinstance(custom_fields_data, str):
					try:
						custom_fields_data = json.loads(custom_fields_data)
					except (json.JSONDecodeError, TypeError):
						custom_fields_data = {}

				# Get custom field definitions for this event to get proper labels and types
				custom_field_defs = frappe.db.get_all(
					"Buzz Custom Field",
					filters={"event": self.event, "enabled": 1, "applied_to": "Ticket"},
					fields=["fieldname", "label", "fieldtype"],
				)
				custom_field_map = {cf["fieldname"]: cf for cf in custom_field_defs}

				for field_name, field_value in custom_fields_data.items():
					if field_value and field_name in custom_field_map:
						field_def = custom_field_map[field_name]
						ticket.append(
							"additional_fields",
							{
								"fieldname": field_name,
								"value": str(field_value),
								"label": field_def["label"],
								"fieldtype": field_def["fieldtype"],
							},
						)

			ticket.flags.ignore_permissions = 1
			ticket.insert().submit()

	def on_payment_authorized(self, payment_status: str):
		if payment_status in ("Authorized", "Completed"):
			# payment success, submit the booking
			self.payment_status = "Paid"
			self.status = "Confirmed"
			self.update_payment_record()

	def update_payment_record(self):
		try:
			mark_payment_as_received(self.doctype, self.name)
			self.flags.ignore_permissions = 1
			self.submit()
		except Exception:
			frappe.log_error(frappe.get_traceback(), _("Booking Failed"))
			frappe.throw(frappe._("Booking Failed! Please contact support."))

	def on_cancel(self):
		self.ignore_linked_doctypes = ["Ticket Cancellation Request"]
		self.cancel_all_tickets()

	def cancel_all_tickets(self):
		tickets = frappe.db.get_all("Event Ticket", filters={"booking": self.name}, pluck="name")
		for ticket in tickets:
			frappe.get_cached_doc("Event Ticket", ticket).cancel()

	@frappe.whitelist()
	def approve_booking(self):
		"""Approve the booking and submit it to generate tickets."""
		frappe.only_for("Event Manager")

		self.status = "Approved"
		if self.payment_status == "Verification Pending":
			self.payment_status = "Paid"

		self.flags.ignore_permissions = True
		self.submit()
		frappe.msgprint(_("Booking has been approved!"))

	@frappe.whitelist()
	def reject_booking(self):
		"""Reject and discard the booking."""
		frappe.only_for("Event Manager")

		self.flags.ignore_permissions = True
		self.discard()
		self.db_set("status", "Rejected")
		frappe.msgprint(_("Booking has been rejected!"))

	def apply_coupon_if_applicable(self):
		self.discount_amount = 0

		if not self.coupon_code:
			return

		coupon = frappe.get_cached_doc("Buzz Coupon Code", self.coupon_code)

		is_valid, error_msg = coupon.is_valid_for_event(self.event)
		if not is_valid:
			frappe.throw(error_msg)

		is_available, error_msg = coupon.is_usage_available()
		if not is_available:
			frappe.throw(error_msg)

		is_limited, error_msg = coupon.is_user_limit_reached(user=self.user)
		if is_limited:
			frappe.throw(error_msg)

		if coupon.coupon_type == "Discount":
			is_met, error_msg = coupon.is_min_order_met(self.net_amount)
			if not is_met:
				frappe.throw(error_msg)
			if coupon.discount_type == "Percentage":
				calculated_discount = self.net_amount * (coupon.discount_value / 100)
				if coupon.maximum_discount_amount > 0:
					self.discount_amount = min(calculated_discount, coupon.maximum_discount_amount)
				else:
					self.discount_amount = calculated_discount
			else:
				self.discount_amount = min(coupon.discount_value, self.net_amount)

			self.total_amount = self.net_amount - self.discount_amount

		# Free Tickets - only discount attendees with matching ticket type
		elif coupon.coupon_type == "Free Tickets":
			remaining = coupon.number_of_free_tickets - coupon.free_tickets_claimed
			free_add_on_names = [row.add_on for row in coupon.free_add_ons]

			# Only discount attendees with matching ticket type
			# Use str() to handle int/string type mismatch in document names
			coupon_ticket_type = str(coupon.ticket_type) if coupon.ticket_type else ""
			discounted = 0
			for attendee in self.attendees:
				if discounted >= remaining:
					break
				attendee_ticket_type = str(attendee.ticket_type) if attendee.ticket_type else ""
				if attendee_ticket_type != coupon_ticket_type:
					continue

				self.discount_amount += attendee.amount
				attendee.amount = 0
				discounted += 1

				# Discount free add-ons for this attendee
				if attendee.add_ons and free_add_on_names:
					add_on_doc = frappe.get_cached_doc("Attendee Ticket Add-on", attendee.add_ons)
					for add_on_row in add_on_doc.add_ons:
						if add_on_row.add_on in free_add_on_names:
							self.discount_amount += add_on_row.price

			if discounted == 0:
				frappe.throw(_("No attendees with eligible ticket type for this coupon"))

			self.total_amount = self.net_amount - self.discount_amount
