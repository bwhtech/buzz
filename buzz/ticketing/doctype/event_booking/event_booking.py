# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt
from collections import Counter

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, cstr, flt, now_datetime

from buzz import telemetry
from buzz.api.booking.exceptions import RegistrationsClosed
from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD, are_registrations_closed
from buzz.api.filters.conditions import form_questions
from buzz.emails import is_full_document
from buzz.events.doctype.buzz_form.form_types import ATTENDEE_FORM_DOCTYPE
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import get_event_team_settings
from buzz.events.online_meeting import OnlineMeeting
from buzz.payments import get_controller, mark_payment_as_received
from buzz.permissions import has_section_permission
from buzz.ticketing.doctype.buzz_coupon_code.buzz_coupon_code import BuzzCouponCode
from buzz.ticketing.doctype.event_booking_refund.event_booking_refund import (
	get_committed_refunds,
	get_committed_tickets,
	record_gateway_refund,
)
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import lock_ticket_types
from buzz.ticketing.doctype.ticket_hold.ticket_hold import (
	PAYMENT_HOLD_MINUTES,
	extend_hold,
	release_hold,
	set_hold,
)
from buzz.utils import build_event_datetimes, render_email_template

RAZORPAY = "Razorpay"


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
		billing_state: DF.Data | None
		business_name: DF.Data | None
		buyer_email: DF.Data | None
		buyer_name: DF.Data | None
		buyer_phone: DF.Data | None
		coupon_code: DF.Link | None
		currency: DF.Link
		discount_amount: DF.Currency
		event: DF.Link
		hold_token: DF.Data | None
		invoice_requested: DF.Check
		naming_series: DF.Literal["B.###"]
		net_amount: DF.Currency
		offline_payment_method: DF.Data | None
		payment_method: DF.Data | None
		payment_status: DF.Literal["Unpaid", "Paid", "Verification Pending"]
		refund_status: DF.Literal["", "Refund Initiated", "Partially Refunded", "Refunded"]
		refunded_amount: DF.Currency
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
		self.validate_event_registration_is_open()
		self.validate_ticket_availability()
		self.fetch_amounts_from_ticket_types()
		self.set_currency()
		self.validate_add_ons_currency()
		self.set_total()
		self.apply_coupon_if_applicable()
		self.apply_taxes_if_applicable()

	def validate_event_registration_is_open(self):
		"""Refuse new bookings for unpublished or closed events, backing up
		`BookingService.validate_event` so the generic document API can't skip it."""
		# A trusted flow has already validated, and payment authorisation or offline
		# approval must still be able to resubmit a draft made before the event closed.
		if self.flags.ignore_permissions:
			return

		event = frappe.get_cached_doc("Buzz Event", self.event)
		if has_section_permission(event.name, "guests", "create", frappe.session.user):
			return

		if not event.is_published:
			frappe.throw(_("Event is not live"))
		if are_registrations_closed(event):
			RegistrationsClosed.throw()

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

	def ticket_quantities(self) -> Counter:
		return Counter(str(attendee.ticket_type) for attendee in self.attendees)

	def validate_ticket_availability(self):
		quantities = self.ticket_quantities()
		ticket_types = [frappe.get_cached_doc("Event Ticket Type", name) for name in quantities]
		lock_ticket_types([row.name for row in ticket_types if row.max_tickets_available])
		for ticket_type in ticket_types:
			self.validate_ticket_type(ticket_type, quantities[str(ticket_type.name)])

	def validate_ticket_type(self, ticket_type, quantity: int):
		if str(ticket_type.event) != str(self.event):
			frappe.throw(_("{0} is not available for this event").format(ticket_type.title))
		if self.flags.payment_received:
			self.log_if_oversold(ticket_type, quantity)
			return
		if not ticket_type.is_published:
			frappe.throw(_("{0} tickets no longer available!").format(ticket_type.title))

		remaining = ticket_type.get_remaining_tickets(for_update=True, hold_token=self.hold_token)
		if remaining == -1 or remaining >= quantity:
			return
		frappe.throw(
			_("Only {0} tickets available for {1}, you are trying to book {2}!").format(
				remaining, ticket_type.title, quantity
			)
		)

	def log_if_oversold(self, ticket_type, quantity: int):
		remaining = ticket_type.get_remaining_tickets(for_update=True, hold_token=self.hold_token)
		if remaining == -1 or remaining >= quantity:
			return
		frappe.log_error(
			title=_("{0} oversold by a payment that arrived late").format(ticket_type.title),
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

	def after_insert(self):
		self.hold_draft_tickets()

	def hold_draft_tickets(self):
		"""A draft that waits for payment or approval keeps its tickets held, so they can't sell
		out under it. Runs right after `validate_ticket_availability` locked the ticket types
		and checked capacity, so it can create the hold even if the form's hold lapsed."""
		if not self.total_amount:
			return
		quantities = {
			name: quantity
			for name, quantity in self.ticket_quantities().items()
			if frappe.get_cached_value("Event Ticket Type", name, "max_tickets_available")
		}
		if not quantities:
			return
		if not self.hold_token:
			self.db_set("hold_token", frappe.generate_hash(length=32), update_modified=False)
		set_hold(self.hold_token, self.event, quantities, self.draft_hold_expiry())

	def draft_hold_expiry(self):
		if self.payment_method == OFFLINE_PAYMENT_METHOD:
			return self.event_end()
		return add_to_date(now_datetime(), minutes=PAYMENT_HOLD_MINUTES)

	def event_end(self):
		_start, end = build_event_datetimes(frappe.get_cached_doc("Buzz Event", self.event))
		return end

	def hold_until_approval(self):
		extend_hold(self.hold_token, self.event_end())

	def fetch_amounts_from_ticket_types(self):
		for attendee in self.attendees:
			ticket_type = frappe.get_cached_doc("Event Ticket Type", attendee.ticket_type)
			attendee.currency = self.currency or ticket_type.prices[0].currency
			attendee.amount = ticket_type.price_in(attendee.currency)

	def validate_add_ons_currency(self):
		for attendee in self.attendees:
			if not attendee.add_ons:
				continue
			add_ons = frappe.get_cached_doc("Attendee Ticket Add-on", attendee.add_ons).add_ons
			if any(row.price and row.currency != self.currency for row in add_ons):
				frappe.throw(_("Paid add-ons can't be paid in {0}").format(self.currency))

	def on_submit(self):
		self.log_if_coupon_overused()
		self.generate_tickets()
		release_hold(self.hold_token)
		self.capture_confirmed()

		try:
			self.send_booking_confirmation_email()
		except Exception:
			frappe.log_error(
				title="Booking confirmation email failed",
				reference_doctype=self.doctype,
				reference_name=self.name,
			)

	def capture_confirmed(self):
		if not self.total_amount:
			payment = "free"
		elif self.payment_method == OFFLINE_PAYMENT_METHOD:
			payment = "offline"
		else:
			payment = "online"

		telemetry.capture(
			"booking_confirmed",
			{
				"payment": payment,
				"attendees": telemetry.count_bucket(len(self.attendees)),
				"coupon": bool(self.coupon_code),
				"add_ons": any(attendee.add_ons for attendee in self.attendees),
				"utm": bool(self.utm_parameters),
				"taxed": bool(self.tax_amount),
			},
		)

	def send_booking_confirmation_email(self):
		event_doc = frappe.get_cached_doc("Buzz Event", self.event)
		team_settings = get_event_team_settings(self.event)
		# Fallback to the team default if event-level not set
		self.send_booking_email(
			template=(
				event_doc.booking_confirmation_email_template
				or team_settings.default_booking_confirmation_email_template
			),
			builtin="booking_confirmation",
			subject=_("Your booking for {0} is confirmed ✅").format(event_doc.title),
		)

	def send_offline_acknowledgement_email(self):
		"""Tell the booker their offline payment is awaiting verification. Sent while the
		booking is still a draft, so the confirmation above stays the approval's job."""
		event_doc = frappe.get_cached_doc("Buzz Event", self.event)
		self.send_booking_email(
			template=event_doc.offline_acknowledgement_email_template,
			builtin="offline_booking_acknowledgement",
			subject=_("We received your booking for {0} — payment verification pending").format(
				event_doc.title
			),
		)

	def send_booking_email(self, template: str | None, builtin: str, subject: str) -> None:
		recipient = self.get_booking_email_recipient()
		if not recipient:
			return

		args = self.get_booking_email_args()

		content = None
		if template:
			email_template = render_email_template(template, args)
			subject = email_template.get("subject") or subject
			content = email_template.get("message")

		full_document = not template or is_full_document(content)
		frappe.sendmail(
			recipients=[recipient],
			subject=subject,
			content=content,
			template=None if template else builtin,
			raw_html=full_document,
			add_css=not full_document,
			args=args,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

	def get_booking_email_recipient(self) -> str | None:
		"""Who to email about this booking, or None when nobody should be emailed."""
		# Never email system/placeholder users — they are not real recipients.
		if self.user in ("Administrator", "Guest"):
			return None

		if not frappe.get_cached_value("Buzz Event", self.event, "send_booking_confirmation_email"):
			return None

		return frappe.db.get_value("User", self.user, "email") or self.user

	def get_booking_email_args(self) -> dict:
		event_doc = frappe.get_cached_doc("Buzz Event", self.event)
		return {
			"doc": self,
			"event_doc": event_doc,
			"meeting": OnlineMeeting(event_doc),
			"event_title": event_doc.title,
			"venue": event_doc.get_venue_name(),
			"attendee_rows": self.get_attendee_email_rows(),
			"support_email": get_event_team_settings(self.event).support_email,
		}

	def get_attendee_email_rows(self) -> list[dict]:
		# Pre-fetch ticket type titles in a single query so the email template
		# loop stays a pure display operation (no per-attendee DB round-trips).
		ticket_type_names = list({attendee.ticket_type for attendee in self.attendees})
		ticket_type_titles = {}
		if ticket_type_names:
			# Ticket types autoname to integers but arrive off the attendee row as
			# strings, so both sides of the lookup are cast before they are compared.
			ticket_type_titles = {
				str(row.name): row.title
				for row in frappe.get_all(
					"Event Ticket Type",
					filters={"name": ["in", ticket_type_names]},
					fields=["name", "title"],
				)
			}

		return [
			{
				"full_name": attendee.full_name
				or " ".join(part for part in (attendee.first_name, attendee.last_name) if part),
				"ticket_type_title": ticket_type_titles.get(str(attendee.ticket_type), attendee.ticket_type),
				"number_of_add_ons": attendee.number_of_add_ons,
				"amount": (attendee.amount or 0) + (attendee.add_on_total or 0),
			}
			for attendee in self.attendees
		]

	def log_if_coupon_overused(self):
		"""`validate` checks the limit before payment; a late payment is booked even past it."""
		if not (self.flags.payment_received and self.coupon_code):
			return
		coupon = frappe.get_doc("Buzz Coupon Code", self.coupon_code)
		if not coupon.usage_limit or coupon.times_used(exclude=self.name) < coupon.usage_limit:
			return
		frappe.log_error(
			title=_("Coupon {0} overused by a payment that arrived late").format(coupon.name),
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

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
						custom_fields_data = frappe.parse_json(custom_fields_data)
					except (ValueError, TypeError):
						custom_fields_data = {}

				# The event's attendee questions give each answer its label and type.
				custom_field_defs = form_questions(self.event, ATTENDEE_FORM_DOCTYPE)
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
			# The money is taken, so a sold-out ticket type or stale coupon must not fail it.
			self.flags.payment_received = True
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
	def get_refund_summary(self) -> dict:
		"""
		Get the amount and tickets still refundable on this booking.

		Returns:
		    committed: amount the gateway has refunded or not answered on yet
		    remaining: booking total minus the committed amount, the most a new refund may be
		    tickets: tickets no committed refund has claimed, from `get_refundable_tickets`
		"""
		# Read by both the refund dialog and `refund`, so what an operator is
		# offered cannot drift from what the server accepts.
		committed = sum(flt(refund.amount) for refund in get_committed_refunds(self.name))

		return {
			"committed": committed,
			"remaining": flt(self.total_amount) - committed,
			"tickets": self.get_refundable_tickets(),
		}

	def get_refundable_tickets(self) -> list[dict]:
		"""
		Get the tickets neither a committed refund nor the front desk has claimed,
		one row per ticket.

		Returns:
		    ticket: name of the Event Ticket
		    attendee: name of whoever the ticket was booked for
		    ticket_type: the attendee's ticket type
		    amount: the ticket's share of what the buyer was charged
		"""
		claimed = get_committed_tickets(self.name)
		attendee_totals = [flt(attendee.amount) + flt(attendee.add_on_total) for attendee in self.attendees]
		booked = sum(attendee_totals)

		# Attendee amounts are pre-tax and pre-discount, so scale them to what was charged.
		charged_share = (flt(self.total_amount) / booked) if booked else 0

		booked_tickets = frappe.get_all(
			"Event Ticket",
			filters={"booking": self.name, "docstatus": 1},
			fields=["name", "attendee_email", "ticket_type"],
			order_by="creation asc",
		)
		used = get_checked_in_tickets([ticket.name for ticket in booked_tickets])

		tickets_by_attendee = {}
		for ticket in booked_tickets:
			tickets_by_attendee.setdefault((ticket.attendee_email, cstr(ticket.ticket_type)), []).append(
				ticket.name
			)

		refundable = []
		for attendee, attendee_total in zip(self.attendees, attendee_totals, strict=True):
			matches = tickets_by_attendee.get((attendee.email, cstr(attendee.ticket_type)))
			if not matches:
				continue

			ticket = matches.pop(0)
			if ticket in claimed or ticket in used:
				continue

			refundable.append(
				{
					"ticket": ticket,
					"attendee": attendee.full_name
					or " ".join(part for part in (attendee.first_name, attendee.last_name) if part),
					"ticket_type": attendee.ticket_type,
					"amount": flt(attendee_total * charged_share, self.precision("total_amount")),
				}
			)

		return refundable

	@frappe.whitelist()
	def refund(self, amount: float, tickets: list[str] | None = None) -> str:
		"""Refund `amount` against this booking's payment."""
		frappe.only_for("System Manager")

		payment = self.get_received_payment()
		if payment.payment_gateway != RAZORPAY:
			frappe.throw(_("Refunds are only supported for Razorpay at the moment"))

		tickets = frappe.parse_json(tickets) if isinstance(tickets, str) else tickets
		self.validate_refund(flt(amount), tickets)

		refund = get_controller(payment.payment_gateway).refund_payment(payment.payment_id, flt(amount))

		# The picked tickets are only recorded here. They are cancelled once the
		# gateway settles the refund, since a refund can still fail. A custom
		# amount maps to no ticket, so it cancels nothing.
		frappe.get_doc(
			{
				"doctype": "Event Booking Refund",
				"booking": self.name,
				"payment": payment.name,
				"refund_id": refund.get("id"),
				"status": "Initiated",
				"amount": flt(refund.get("amount")) / 100,
				"currency": self.currency,
				"tickets": [{"ticket": ticket} for ticket in tickets or []],
			}
		).insert()

		self.set_refund_status()

		return self.refund_status

	@frappe.whitelist()
	def sync_refunds(self) -> dict:
		"""Reconcile this booking's refunds against what Razorpay actually holds."""
		frappe.only_for("System Manager")

		payment = self.get_received_payment()
		if payment.payment_gateway != RAZORPAY:
			frappe.throw(_("Refunds are only supported for Razorpay at the moment"))

		# Razorpay lists the newest refund first, and each one recorded moves what
		# is left to refund, so they are applied in the order they were raised.
		refunds = list(reversed(get_controller(payment.payment_gateway).fetch_refunds(payment.payment_id)))

		return {
			"refunds": len(refunds),
			"created": sum(self.record_refund(payment, refund) for refund in refunds),
		}

	def record_refund(self, payment, gateway_refund: dict) -> bool:
		"""Record one gateway refund against this booking. True when it was new."""
		return record_gateway_refund(
			booking=self.name,
			payment=payment.name,
			refund_id=gateway_refund.get("id"),
			status=gateway_refund.get("status"),
			amount=flt(gateway_refund.get("amount")) / 100,
		)

	def validate_refund(self, amount: float, tickets: list[str] | None = None) -> None:
		summary = self.get_refund_summary()

		if amount <= 0:
			frappe.throw(_("Refund amount must be greater than 0"))

		if amount > summary["remaining"]:
			frappe.throw(
				_("Only {0} is left to refund on this booking").format(
					frappe.format_value(
						summary["remaining"], {"fieldtype": "Currency", "options": "currency"}, self
					)
				)
			)

		if get_checked_in_tickets(tickets or []):
			# The attendee has been through the door, so the ticket has been used.
			frappe.throw(_("A ticket that has been checked in cannot be refunded"))

		refundable = {ticket["ticket"] for ticket in summary["tickets"]}
		if not set(tickets or []) <= refundable:
			# Ticket belongs to another booking, or an earlier refund claimed it.
			frappe.throw(_("Those tickets cannot be refunded against this booking"))

	def set_refund_status(self) -> None:
		"""Recompute refunded amount and status from the refunds against this booking."""
		refunds = frappe.get_all(
			"Event Booking Refund", filters={"booking": self.name}, fields=["amount", "status"]
		)
		self.refunded_amount = sum(flt(refund.amount) for refund in refunds if refund.status == "Processed")

		if self.refunded_amount >= flt(self.total_amount):
			status = "Refunded"
		elif self.refunded_amount:
			status = "Partially Refunded"
		elif any(refund.status == "Initiated" for refund in refunds):
			status = "Refund Initiated"
		else:
			status = ""

		self.db_set({"refunded_amount": self.refunded_amount, "refund_status": status}, notify=True)

	def get_received_payment(self):
		payment = frappe.get_all(
			"Event Payment",
			filters={
				"reference_doctype": self.doctype,
				"reference_docname": self.name,
				"payment_received": 1,
			},
			fields=["name", "payment_gateway", "payment_id", "amount"],
			order_by="creation desc",
			limit=1,
		)

		if not payment or not payment[0].payment_id:
			frappe.throw(_("No received payment found for this booking"))

		return payment[0]

	@frappe.whitelist()
	def approve_booking(self):
		"""Approve the booking and submit it to generate tickets."""
		frappe.only_for("Event Manager")

		self.status = "Approved"
		self.flags.payment_received = True
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
		release_hold(self.hold_token)
		frappe.msgprint(_("Booking has been rejected!"))

	def apply_coupon_if_applicable(self):
		self.discount_amount = 0
		coupon = self.get_coupon()
		self.coupon_code = coupon.name if coupon else None
		if coupon:
			self.discount_amount = coupon.discount_for(self)
			self.total_amount = self.net_amount - self.discount_amount

	def get_coupon(self) -> BuzzCouponCode | None:
		if self.flags.payment_received:
			# The buyer paid this price, so keep the coupon it was quoted with.
			return frappe.get_doc("Buzz Coupon Code", self.coupon_code) if self.coupon_code else None
		BuzzCouponCode.lock_for(self)
		if not self.coupon_code:
			return BuzzCouponCode.best_automatic(self)
		coupon = frappe.get_doc("Buzz Coupon Code", self.coupon_code)
		if reason := coupon.unusable_reason(self):
			frappe.throw(reason)
		return coupon


def get_checked_in_tickets(tickets: list[str]) -> set[str]:
	"""Of the tickets given, the ones whose attendee has already been through the door."""
	if not tickets:
		return set()

	return set(
		frappe.get_all("Event Check In", filters={"ticket": ("in", tickets), "docstatus": 1}, pluck="ticket")
	)
