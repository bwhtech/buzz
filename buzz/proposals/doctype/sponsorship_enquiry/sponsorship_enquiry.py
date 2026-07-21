# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.model.document import Document
from frappe.utils import get_url

from buzz.payments import mark_payment_as_received


class SponsorshipEnquiry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company_logo: DF.AttachImage
		company_name: DF.Data
		country: DF.Link | None
		event: DF.Link
		phone: DF.Phone | None
		status: DF.Literal["Approval Pending", "Payment Pending", "Paid", "Withdrawn"]
		tier: DF.Link | None
		website: DF.Data | None
	# end: auto-generated types

	def on_update(self):
		if self.has_value_changed("status") and self.status == "Payment Pending":
			try:
				self.send_approval_notification()
			except Exception:
				frappe.log_error("Error sending Sponsorship Approval Notification")

	def on_payment_authorized(self, payment_status: str):
		if payment_status in ("Authorized", "Completed"):
			mark_payment_as_received(self.doctype, self.name)
			frappe.get_doc(
				{
					"doctype": "Event Sponsor",
					"company_name": self.company_name,
					"company_logo": self.company_logo,
					"event": self.event,
					"tier": self.tier,
					"enquiry": self.name,
					"website": self.website,
				}
			).insert(ignore_permissions=True)
			self.db_set("status", "Paid")

	@frappe.whitelist()
	def create_sponsor(self):
		frappe.only_for("Event Manager")

		if not self.tier:
			frappe.throw(frappe._("Please select a sponsorship tier!"))

		frappe.get_doc(
			{
				"doctype": "Event Sponsor",
				"company_name": self.company_name,
				"company_logo": self.company_logo,
				"event": self.event,
				"tier": self.tier,
				"enquiry": self.name,
				"website": self.website,
				"country": self.country,
			}
		).insert(ignore_permissions=True)

	def after_insert(self):
		try:
			self.send_pitch_deck()
		except Exception:
			frappe.log_error("Error sending Sponsor Pitch Deck")

	def send_pitch_deck(self, now=False):
		event = frappe.get_cached_doc("Buzz Event", self.event)
		settings = frappe.get_cached_doc("Buzz Settings")

		# Check event-level toggle first, then fall back to global
		if not event.auto_send_pitch_deck and not settings.auto_send_pitch_deck:
			return

		# Get template: event-level takes precedence, fall back to global
		template_name = event.sponsor_deck_email_template or settings.default_sponsor_deck_email_template
		if not template_name:
			frappe.log_error("No sponsor deck email template configured", "Sponsorship Enquiry")
			return

		email_template = get_email_template(template_name, {"doc": self, "event": event})

		subject = email_template.get("subject")
		content = email_template.get("message")

		# Get CC and Reply-To: event-level takes precedence
		cc = event.sponsor_deck_cc or settings.default_sponsor_deck_cc
		reply_to = event.sponsor_deck_reply_to or settings.default_sponsor_deck_reply_to

		frappe.sendmail(
			recipients=[self.owner],
			subject=subject,
			cc=cc,
			reply_to=reply_to,
			content=content,
			reference_doctype=self.doctype,
			reference_name=self.name,
			now=now,
			attachments=[{"file_url": attachment.file} for attachment in event.sponsor_deck_attachments],
		)

	def send_approval_notification(self):
		event = frappe.get_cached_doc("Buzz Event", self.event)
		host_name = event.host or "The Event Team"
		dashboard_link = get_url(f"/b/account/sponsorships/{self.name}")

		subject = f"[Payment Pending] Your Sponsorship for {event.title} has been Approved!"
		message = f"""
		<p>Dear {self.company_name},</p>

		<p>We are pleased to inform you that your sponsorship enquiry for <strong>{event.title}</strong> has been approved.</p>

		<p>You can now proceed to select a sponsorship tier and complete the payment by visiting your dashboard <a href="{dashboard_link}">here</a>.</p>

		<br>{host_name}</p>
		"""

		frappe.sendmail(
			recipients=[self.owner],
			subject=subject,
			message=message,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)
