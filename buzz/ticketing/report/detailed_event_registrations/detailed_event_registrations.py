# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from buzz.api.filters.conditions import registration_questions
from buzz.booking_permissions import ensure_guests_access


def execute(filters=None):
	if not filters:
		filters = {}

	ensure_guests_access(filters.get("event"))
	if not filters.get("event"):
		return [], []

	columns = get_columns(filters)
	data = get_data(filters, columns)
	return columns, data


def get_columns(filters):
	event = filters.get("event")

	# Fixed columns
	columns = [
		{
			"fieldname": "ticket_id",
			"label": _("Ticket ID"),
			"fieldtype": "Link",
			"options": "Event Ticket",
			"width": 120,
		},
		{
			"fieldname": "attendee_name",
			"label": _("Attendee Name"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "attendee_email",
			"label": _("Attendee Email"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "booking_id",
			"label": _("Booking ID"),
			"fieldtype": "Link",
			"options": "Event Booking",
			"width": 120,
		},
		{
			"fieldname": "ticket_type",
			"label": _("Ticket Type"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "booking_user",
			"label": _("Booking User"),
			"fieldtype": "Link",
			"options": "User",
			"width": 150,
		},
		{
			"fieldname": "booked_at",
			"label": _("Booked At"),
			"fieldtype": "Datetime",
			"width": 160,
		},
	]

	# Dynamic custom field columns
	custom_fields = get_custom_fields_for_event(event)
	for cf in custom_fields:
		columns.append(
			{
				"fieldname": f"cf_{cf.fieldname}",
				"label": _(cf.label),
				"fieldtype": "Data",
				"width": 180,
			}
		)

	# Dynamic add-on columns
	add_ons = get_add_ons_for_event(event)
	for addon in add_ons:
		columns.append(
			{
				"fieldname": f"addon_{addon.name}",
				"label": _(addon.title),
				"fieldtype": "Data",
				"width": 150,
			}
		)

	# Dynamic UTM parameter columns
	utm_params = get_utm_params_for_event(event)
	for utm in utm_params:
		columns.append(
			{
				"fieldname": f"utm_{utm}",
				"label": _(utm.replace("_", " ").title()),
				"fieldtype": "Data",
				"width": 150,
			}
		)

	return columns


def get_data(filters, columns):
	event = filters.get("event")

	# Get all submitted tickets for the event
	tickets = frappe.get_all(
		"Event Ticket",
		filters={"event": event, "docstatus": 1},
		fields=["name", "attendee_name", "attendee_email", "booking", "ticket_type", "creation"],
	)

	if not tickets:
		return []

	# Get ticket type titles
	ticket_type_map = get_ticket_type_map(event)

	# Get booking details
	booking_ids = list(set([t.booking for t in tickets if t.booking]))
	booking_map = get_booking_map(booking_ids)

	# Get custom fields configuration
	custom_fields = get_custom_fields_for_event(event)
	custom_field_names = [cf.fieldname for cf in custom_fields]

	# Get add-ons configuration
	add_ons = get_add_ons_for_event(event)
	add_on_names = [addon.name for addon in add_ons]

	# Get UTM params
	utm_params = get_utm_params_for_event(event)

	# Get ticket additional fields
	ticket_ids = [t.name for t in tickets]
	ticket_additional_fields = get_ticket_additional_fields(ticket_ids)

	# Get booking additional fields
	booking_additional_fields = get_booking_additional_fields(booking_ids)

	# Get ticket add-ons
	ticket_add_ons = get_ticket_add_ons(ticket_ids)

	# Get booking UTM parameters
	booking_utm_params = get_booking_utm_params(booking_ids)

	# Build data rows
	data = []
	for ticket in tickets:
		row = {
			"ticket_id": ticket.name,
			"attendee_name": ticket.attendee_name,
			"attendee_email": ticket.attendee_email,
			"booking_id": ticket.booking,
			"ticket_type": ticket_type_map.get(str(ticket.ticket_type), ticket.ticket_type),
			"booking_user": booking_map.get(ticket.booking, {}).get("user", ""),
			"booked_at": ticket.creation,
		}

		# Add custom field values (ticket takes priority over booking)
		for cf_name in custom_field_names:
			ticket_cf_value = ticket_additional_fields.get(ticket.name, {}).get(cf_name)
			booking_cf_value = booking_additional_fields.get(ticket.booking, {}).get(cf_name)
			row[f"cf_{cf_name}"] = ticket_cf_value or booking_cf_value or ""

		# Add add-on values
		for addon_name in add_on_names:
			addon_value = ticket_add_ons.get(ticket.name, {}).get(addon_name)
			row[f"addon_{addon_name}"] = addon_value or ""

		# Add UTM parameter values
		for utm in utm_params:
			utm_value = booking_utm_params.get(ticket.booking, {}).get(utm)
			row[f"utm_{utm}"] = utm_value or ""

		data.append(row)

	return data


def get_custom_fields_for_event(event):
	return [
		frappe._dict(
			fieldname=question.fieldname,
			label=question.label,
			applied_to=question.applied_to,
		)
		for question in registration_questions(event)
	]


def get_add_ons_for_event(event):
	return frappe.get_all(
		"Ticket Add-on",
		filters={"event": event, "enabled": 1},
		fields=["name", "title"],
		order_by="creation asc",
	)


def get_utm_params_for_event(event):
	# Get distinct UTM parameter names from bookings for this event
	utm_data = frappe.db.sql(
		"""
		SELECT DISTINCT up.utm_name
		FROM `tabUTM Parameter` up
		INNER JOIN `tabEvent Booking` eb ON up.parent = eb.name
		WHERE eb.event = %s AND eb.docstatus = 1
		ORDER BY up.utm_name
	""",
		(event,),
		as_dict=True,
	)
	return [u.utm_name for u in utm_data]


def get_ticket_type_map(event):
	ticket_types = frappe.get_all(
		"Event Ticket Type",
		filters={"event": event},
		fields=["name", "title"],
	)
	# Use string keys to handle type mismatches (autoincrement IDs can be int or str)
	return {str(tt.name): tt.title for tt in ticket_types}


def get_booking_map(booking_ids):
	if not booking_ids:
		return {}

	bookings = frappe.get_all(
		"Event Booking",
		filters={"name": ["in", booking_ids]},
		fields=["name", "user"],
	)
	return {b.name: b for b in bookings}


def get_ticket_additional_fields(ticket_ids):
	if not ticket_ids:
		return {}

	additional_fields = frappe.get_all(
		"Additional Field",
		filters={"parent": ["in", ticket_ids], "parenttype": "Event Ticket"},
		fields=["parent", "fieldname", "value"],
	)

	result = {}
	for af in additional_fields:
		if af.parent not in result:
			result[af.parent] = {}
		result[af.parent][af.fieldname] = af.value

	return result


def get_booking_additional_fields(booking_ids):
	if not booking_ids:
		return {}

	additional_fields = frappe.get_all(
		"Additional Field",
		filters={"parent": ["in", booking_ids], "parenttype": "Event Booking"},
		fields=["parent", "fieldname", "value"],
	)

	result = {}
	for af in additional_fields:
		if af.parent not in result:
			result[af.parent] = {}
		result[af.parent][af.fieldname] = af.value

	return result


def get_ticket_add_ons(ticket_ids):
	if not ticket_ids:
		return {}

	add_ons = frappe.get_all(
		"Ticket Add-on Value",
		filters={"parent": ["in", ticket_ids], "parenttype": "Event Ticket"},
		fields=["parent", "add_on", "value"],
	)

	result = {}
	for ao in add_ons:
		if ao.parent not in result:
			result[ao.parent] = {}
		result[ao.parent][ao.add_on] = ao.value

	return result


def get_booking_utm_params(booking_ids):
	if not booking_ids:
		return {}

	utm_params = frappe.get_all(
		"UTM Parameter",
		filters={"parent": ["in", booking_ids], "parenttype": "Event Booking"},
		fields=["parent", "utm_name", "value"],
	)

	result = {}
	for up in utm_params:
		if up.parent not in result:
			result[up.parent] = {}
		result[up.parent][up.utm_name] = up.value

	return result
