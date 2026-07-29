from typing import TYPE_CHECKING

import frappe
from frappe import _

from buzz.api.booking.schemas import EventBookingDataResponse, TaxSettings
from buzz.api.booking.services import are_registrations_closed
from buzz.payments import get_payment_gateways_for_event

if TYPE_CHECKING:
	from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent


def build_event_booking_data(event_route: str) -> EventBookingDataResponse:
	event_doc = frappe.get_cached_doc("Buzz Event", {"route": event_route})

	if not event_doc.is_published:
		frappe.throw(_("Event not found"), frappe.DoesNotExistError)

	payment_gateways = get_payment_gateways_for_event(event_doc.name)
	offline_methods = get_offline_methods(event_doc.name)
	payment_gateways += [method["title"] for method in offline_methods]

	return EventBookingDataResponse(
		registrations_closed=are_registrations_closed(event_doc),
		event_details=get_event_details(event_doc),
		available_ticket_types=get_available_ticket_types(event_doc.name),
		available_add_ons=get_available_add_ons(event_doc.name),
		tax_settings=TaxSettings(
			apply_tax=event_doc.apply_tax,
			tax_inclusive=event_doc.tax_inclusive,
			tax_label=event_doc.tax_label or "Tax",
			tax_percentage=event_doc.tax_percentage or 0,
		),
		custom_fields=get_custom_fields(event_doc.name, applied_to=None),
		payment_gateways=payment_gateways,
		offline_payment_enabled=len(offline_methods) > 0,
		offline_methods=offline_methods,
	)


def get_event_details(event_doc: "BuzzEvent"):
	if frappe.session.user != "Guest":
		return event_doc

	return {
		"name": event_doc.name,
		"title": event_doc.title,
		"route": event_doc.route,
		"start_date": event_doc.start_date,
		"end_date": event_doc.end_date,
		"start_time": event_doc.start_time,
		"end_time": event_doc.end_time,
		"time_zone": event_doc.time_zone,
		"time_zone_label": event_doc.time_zone_label,
		"venue": event_doc.venue,
		"medium": event_doc.medium,
		"category": event_doc.category,
		"banner_image": event_doc.banner_image,
		"short_description": event_doc.short_description,
		"free_event": event_doc.free_event,
		"send_ticket_email": event_doc.send_ticket_email,
		"allow_guest_booking": event_doc.allow_guest_booking,
		"guest_verification_method": event_doc.guest_verification_method,
		"default_ticket_type": event_doc.default_ticket_type,
	}


def get_available_ticket_types(event_id: str) -> list:
	published_ticket_types = frappe.db.get_all(
		"Event Ticket Type", filters={"is_published": True, "event": event_id}, pluck="name"
	)
	available_ticket_types = []
	for ticket_type in published_ticket_types:
		ticket_type_doc = frappe.get_cached_doc("Event Ticket Type", ticket_type)
		if ticket_type_doc.are_tickets_available(1):
			available_ticket_types.append(ticket_type_doc)
	return available_ticket_types


def get_available_add_ons(event_id: str) -> list:
	add_ons = frappe.db.get_all(
		"Ticket Add-on", filters={"event": event_id, "enabled": 1}, fields=["*"], order_by="title"
	)
	for add_on in add_ons:
		if add_on.user_selects_option:
			add_on.options = add_on.options.split("\n")
	return add_ons


def get_custom_fields(
	event_id: str, applied_to: str | None, offline_payment_method: str | None = None
) -> list:
	filters = {"event": event_id, "enabled": 1}
	if applied_to:
		filters["applied_to"] = applied_to
	if offline_payment_method:
		filters["offline_payment_method"] = offline_payment_method
	return frappe.db.get_all("Buzz Custom Field", filters=filters, fields=["*"], order_by="order")


def get_offline_methods(event_id: str) -> list:
	methods = frappe.get_all(
		"Offline Payment Method",
		filters={"event": event_id, "enabled": 1},
		fields=["name", "title", "description", "collect_payment_proof"],
		order_by="creation",
	)
	return [
		{
			"name": method.name,
			"title": method.title,
			"description": method.description,
			"collect_payment_proof": method.collect_payment_proof,
			"custom_fields": get_custom_fields(
				event_id, applied_to="Offline Payment Form", offline_payment_method=method.name
			),
		}
		for method in methods
	]
