# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.core.api.user_invitation import invite_by_email
from frappe.model.document import Document

from buzz.utils import generate_ics_file, generate_qr_code_file, only_if_app_installed


class EventTicket(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.ticketing.doctype.additional_field.additional_field import AdditionalField
		from buzz.ticketing.doctype.ticket_add_on_value.ticket_add_on_value import TicketAddonValue

		add_ons: DF.Table[TicketAddonValue]
		additional_fields: DF.Table[AdditionalField]
		amended_from: DF.Link | None
		attendee_email: DF.Data
		attendee_name: DF.Data
		booking: DF.Link | None
		coupon_used: DF.Link | None
		event: DF.Link | None
		first_name: DF.Data
		last_name: DF.Data | None
		qr_code: DF.AttachImage | None
		ticket_type: DF.Link
	# end: auto-generated types

	def before_validate(self):
		# Backward compat: split attendee_name into first/last if first_name not provided
		if not self.first_name and self.attendee_name:
			name_parts = self.attendee_name.strip().split(" ", 1)
			self.first_name = name_parts[0]
			if not self.last_name and len(name_parts) > 1:
				self.last_name = name_parts[1]

	def validate(self):
		self.attendee_name = f"{self.first_name or ''} {self.last_name or ''}".strip()

	def before_submit(self):
		self.validate_coupon_usage()
		self.generate_qr_code()

	def on_submit(self):
		try:
			self.send_ticket_email()
		except Exception as e:
			frappe.log_error("Error sending ticket email: " + str(e))

		# TODO: bring back after we have templates
		# try:
		# 	self.send_user_invitation()
		# except Exception as e:
		# 	frappe.log_error("Error sending user invitation: " + str(e))
		self.create_zoom_registration_if_applicable()

	@only_if_app_installed("zoom_integration")
	def create_zoom_registration_if_applicable(self):
		event_doc = frappe.get_cached_doc("Buzz Event", self.event)

		if event_doc.zoom_webinar:
			doc = {
				"doctype": "Zoom Webinar Registration",
				"webinar": event_doc.zoom_webinar,
				"email": self.attendee_email,
				"first_name": self.first_name,
				"last_name": self.last_name or "-",
			}
			registration = frappe.get_doc(doc).insert(ignore_permissions=True)

			try:
				registration.submit()
				# Store the registration reference on the ticket
				self.db_set("zoom_webinar_registration", registration.name)
			except Exception:
				frappe.log_error("Failed to create registration on Zoom")

	def send_user_invitation(self):
		invite_by_email(
			emails=self.attendee_email,
			roles=["Buzz User"],
			redirect_to_path="/b/account/tickets",
			app_name="buzz",
		)

	def send_ticket_email(self, now: bool = False):
		send_ticket_email = frappe.get_cached_value("Buzz Event", self.event, "send_ticket_email")

		if not send_ticket_email:
			return

		event_title, ticket_template, ticket_print_format, venue = frappe.get_cached_value(
			"Buzz Event", self.event, ["title", "ticket_email_template", "ticket_print_format", "venue"]
		)

		# Fallback to global setting if event-level not set
		if not ticket_template:
			ticket_template = frappe.db.get_single_value("Buzz Settings", "default_ticket_email_template")

		subject = frappe._("Your ticket to {0} 🎟️").format(event_title)
		event_doc = frappe.get_cached_doc("Buzz Event", self.event)
		args = {
			"doc": self,
			"event_doc": event_doc,
			"event_title": event_title,
			"venue": venue,
		}

		if ticket_template:
			from frappe.email.doctype.email_template.email_template import get_email_template

			email_template = get_email_template(ticket_template, args)
			subject = email_template.get("subject")
			content = email_template.get("message")

		attachments = []

		if event_doc.attach_email_ticket:
			attachments.append(
				{
					"print_format_attachment": 1,
					"doctype": self.doctype,
					"name": self.name,
					"print_format": ticket_print_format or "Standard Ticket",
				}
			)

		if event_doc.attach_calendar_invite:
			ics_content = generate_ics_file(event_doc, self.attendee_email)
			attachments.append(
				{
					"fname": f"{event_doc.title}.ics",
					"fcontent": ics_content,
				}
			)

		frappe.sendmail(
			recipients=[self.attendee_email],
			subject=subject,
			content=content if ticket_template else None,
			template="ticket" if not ticket_template else None,
			args=args,
			reference_doctype=self.doctype,
			reference_name=self.name,
			now=now,
			attachments=attachments,
		)

	def validate_coupon_usage(self):
		if not self.coupon_used:
			return

		coupon = frappe.get_cached_doc("Bulk Ticket Coupon", self.coupon_used)
		if coupon.is_used_up():
			frappe.throw(frappe._("Coupon has been already used up maximum number of times!"))

	def generate_qr_code(self):
		self.qr_code = generate_qr_code_file(
			doc=self,
			data=self.name,
			file_prefix="ticket-qr-code",
		)

	def on_cancel(self):
		self.ignore_linked_doctypes = ["Event Booking", "Ticket Cancellation Request"]
		self.send_cancellation_email()

	def send_cancellation_email(self):
		event_title = frappe.get_cached_value("Buzz Event", self.event, "title")
		frappe.sendmail(
			recipients=self.attendee_email,
			subject=f"Your ticket to {event_title} is cancelled.",
			message=f"Hi {self.attendee_name}, your ticket has been cancelled successfully. Sad to see you go.",
			header=[("Ticket Cancelled"), "red"],
			delayed=False,
			retry=2,
		)
