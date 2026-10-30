# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from buzz.booking_permissions import ensure_guests_access


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	ensure_guests_access((filters or {}).get("event"))
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	"""Return columns for the report.

	One field definition per column, just like a DocType field definition.
	"""
	return [
		{
			"label": _("Attendee Name"),
			"fieldname": "attendee_name",
			"fieldtype": "Data",
		},
		{"label": _("Attendee Email"), "fieldname": "attendee_email", "fieldtype": "Data", "width": 200},
		{"label": _("Add-On"), "fieldname": "add_on", "fieldtype": "Data", "width": 150},
		{"label": _("Value"), "fieldname": "value", "fieldtype": "Data", "width": 150},
		{
			"label": _("Ticket"),
			"fieldname": "ticket",
			"fieldtype": "Link",
			"options": "Event Ticket",
			"width": 150,
		},
	]


def get_data(filters=None) -> list[dict]:
	"""Return data for the report.

	The report data is a list of rows, with each row being a list of cell values.
	"""
	tav = frappe.qb.DocType("Ticket Add-on Value")
	ticket = frappe.qb.DocType("Event Ticket")
	ticket_add_on = frappe.qb.DocType("Ticket Add-on")

	if not filters:
		filters = {}

	query = (
		frappe.qb.from_(tav)
		.join(ticket)
		.on(tav.parent == ticket.name)
		.join(ticket_add_on)
		.on(tav.add_on == ticket_add_on.name)
		.select(
			ticket.attendee_name,
			ticket.attendee_email,
			ticket.name.as_("ticket"),
			ticket_add_on.title.as_("add_on"),
			tav.value,
		)
		.where(ticket.event == filters.get("event"))
		.where(ticket.docstatus == 1)
	)

	if filters.get("add_on_type"):
		query = query.where(ticket_add_on.name == filters.get("add_on_type"))

	if filters.get("add_on_value"):
		# like operator for partial matching
		query = query.where(tav.value.like(f"%{filters.get('add_on_value')}%"))

	return query.run(as_dict=True)
