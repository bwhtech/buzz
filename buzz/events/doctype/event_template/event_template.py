# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buzz.events.doctype.buzz_form.form_types import QUESTION_FIELD_NAMES, SPONSORSHIP_FORM_DOCTYPE
from buzz.ticketing.doctype.event_ticket_category.event_ticket_category import get_ordered_categories


class EventTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.event_payment_gateway.event_payment_gateway import EventPaymentGateway
		from buzz.events.doctype.event_template_add_on.event_template_add_on import EventTemplateAddon
		from buzz.events.doctype.event_template_custom_field.event_template_custom_field import (
			EventTemplateCustomField,
		)
		from buzz.events.doctype.event_template_ticket_category.event_template_ticket_category import (
			EventTemplateTicketCategory,
		)
		from buzz.events.doctype.event_template_ticket_type.event_template_ticket_type import (
			EventTemplateTicketType,
		)
		from buzz.proposals.doctype.sponsorship_deck_item.sponsorship_deck_item import SponsorshipDeckItem

		about: DF.TextEditor | None
		allow_guest_booking: DF.Check
		apply_tax: DF.Check
		auto_send_pitch_deck: DF.Check
		banner_image: DF.AttachImage | None
		category: DF.Link | None
		guest_verification_method: DF.Literal["None", "Email OTP", "Phone OTP"]
		host: DF.Link | None
		medium: DF.Literal["In Person", "Online"]
		payment_gateways: DF.Table[EventPaymentGateway]
		send_ticket_email: DF.Check
		short_description: DF.SmallText | None
		sponsor_deck_attachments: DF.Table[SponsorshipDeckItem]
		sponsor_deck_cc: DF.SmallText | None
		sponsor_deck_email_template: DF.Link | None
		sponsor_deck_reply_to: DF.Data | None
		tax_label: DF.Data | None
		tax_percentage: DF.Percent
		team: DF.Link
		template_add_ons: DF.Table[EventTemplateAddon]
		template_custom_fields: DF.Table[EventTemplateCustomField]
		template_name: DF.Data
		template_ticket_categories: DF.Table[EventTemplateTicketCategory]
		template_ticket_types: DF.Table[EventTemplateTicketType]
		ticket_email_template: DF.Link | None
		ticket_print_format: DF.Link | None
		time_zone: DF.Autocomplete | None
		venue: DF.Link | None
	# end: auto-generated types

	pass


@frappe.whitelist()
def create_template_from_event(event_name: str, template_name: str, options: str) -> str:
	"""
	Create an Event Template from an existing Buzz Event.

	Args:
	    event_name: Name of the source Buzz Event
	    template_name: Name for the new template
	    options: JSON string of what to include

	Returns:
	    New Event Template document name
	"""
	if not frappe.has_permission("Event Template", "create"):
		frappe.throw(_("You don't have permission to create templates"))

	event = frappe.get_doc("Buzz Event", event_name)
	options = frappe.parse_json(options)

	template = frappe.new_doc("Event Template")
	template.template_name = template_name

	# Field mapping for direct copy
	field_map = {
		"category": "category",
		"host": "host",
		"banner_image": "banner_image",
		"short_description": "short_description",
		"about": "about",
		"medium": "medium",
		"venue": "venue",
		"allow_guest_booking": "allow_guest_booking",
		"guest_verification_method": "guest_verification_method",
		"time_zone": "time_zone",
		"send_ticket_email": "send_ticket_email",
		"ticket_email_template": "ticket_email_template",
		"ticket_print_format": "ticket_print_format",
		"apply_tax": "apply_tax",
		"tax_label": "tax_label",
		"tax_percentage": "tax_percentage",
		"auto_send_pitch_deck": "auto_send_pitch_deck",
		"sponsor_deck_email_template": "sponsor_deck_email_template",
		"sponsor_deck_reply_to": "sponsor_deck_reply_to",
		"sponsor_deck_cc": "sponsor_deck_cc",
	}

	for option_key, field_name in field_map.items():
		if options.get(option_key):
			template.set(field_name, event.get(field_name))

	# Copy child tables from event
	if options.get("payment_gateways"):
		for pg in event.payment_gateways:
			template.append("payment_gateways", {"payment_gateway": pg.payment_gateway})

	if options.get("sponsor_deck_attachments"):
		for attachment in event.sponsor_deck_attachments:
			template.append("sponsor_deck_attachments", {"file": attachment.file})

	# Copy linked documents (Ticket Types, Add-ons, Custom Fields)
	if options.get("ticket_types"):
		categories = get_ordered_categories(event_name)
		for category in categories:
			template.append(
				"template_ticket_categories",
				{key: category[key] for key in ("title", "description", "sort_order")},
			)
		category_titles = {category.name: category.title for category in categories}
		ticket_types = frappe.get_all(
			"Event Ticket Type",
			filters={"event": event_name},
			fields=[
				"title",
				"category",
				{"prices": ["currency", "price"]},
				"is_published",
				"max_tickets_available",
				"auto_unpublish_after",
			],
		)
		for tt in ticket_types:
			template.append(
				"template_ticket_types",
				{
					"title": tt.title,
					"category": category_titles.get(tt.category),
					"price": tt.prices[0].price,
					"currency": tt.prices[0].currency,
					"is_published": tt.is_published,
					"max_tickets_available": tt.max_tickets_available,
					"auto_unpublish_after": tt.auto_unpublish_after,
				},
			)

	if options.get("add_ons"):
		add_ons = frappe.get_all(
			"Ticket Add-on",
			filters={"event": event_name},
			fields=["title", "price", "currency", "description", "user_selects_option", "options", "enabled"],
		)
		for addon in add_ons:
			template.append(
				"template_add_ons",
				{
					"title": addon.title,
					"price": addon.price,
					"currency": addon.currency,
					"description": addon.description,
					"user_selects_option": addon.user_selects_option,
					"options": addon.options,
					"enabled": addon.enabled,
				},
			)

	if options.get("custom_fields"):
		for custom_field in event_template_questions(event_name):
			template.append("template_custom_fields", custom_field)

	template.insert()
	return template.name


def event_template_questions(event_name: str) -> list[dict]:
	# Sponsorship questions stay on the event's own sponsorship form, which every event has.
	forms = {
		form.name: form.form_doctype
		for form in frappe.get_all(
			"Buzz Form",
			filters={"event": event_name, "form_doctype": ["!=", SPONSORSHIP_FORM_DOCTYPE]},
			fields=["name", "form_doctype"],
		)
	}
	questions = frappe.get_all(
		"Buzz Form Field",
		filters={"parenttype": "Buzz Form", "parent": ["in", list(forms)], "is_standard": 0},
		fields=["parent", *QUESTION_FIELD_NAMES],
		order_by="parent, idx",
	)
	return [
		{
			**{name: question.get(name) for name in QUESTION_FIELD_NAMES},
			"form_doctype": forms[question.parent],
		}
		for question in questions
	]
