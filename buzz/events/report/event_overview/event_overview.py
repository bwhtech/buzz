# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from buzz.booking_permissions import ensure_guests_access, guest_section_events


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	"""Return columns for the report.

	One field definition per column, just like a DocType field definition.
	"""
	return [
		{
			"label": _("Event"),
			"fieldname": "event",
			"fieldtype": "Link",
			"options": "Buzz Event",
			"width": 200,
		},
		{
			"label": _("Number of Tickets Sold"),
			"fieldname": "num_tickets_sold",
			"fieldtype": "Int",
		},
		{"label": _("Number of Add-ons Sold"), "fieldname": "num_add_ons_sold", "fieldtype": "Int"},
		{"label": _("Ticket Sales"), "fieldname": "sales", "fieldtype": "Currency"},
	]


def get_data(filters: dict) -> list[dict]:
	"""Return data for the report.

	The report data is a list of rows, with each row being a list of cell values.
	"""
	event = filters.get("event")
	ensure_guests_access(event)

	if event:
		return [get_summary_for_event(event)]

	data = []
	events = guest_section_events()
	for event in events:
		summary = get_summary_for_event(event)
		summary["event"] = event
		data.append(summary)

	return data


def get_summary_for_event(event: str) -> dict:
	"""Return summary data for the event.

	This function is used to get a summary of the event, such as total tickets sold,
	total add-ons sold, and total sales.
	"""
	event_tickets = frappe.db.get_all("Event Ticket", filters={"event": event, "docstatus": 1}, pluck="name")
	num_tickets_sold = len(event_tickets)
	sales = frappe.db.get_all(
		"Event Booking",
		filters={"docstatus": 1, "event": event},
		fields=[{"SUM": "total_amount", "as": "sales"}],
		pluck="sales",
	)[0]

	num_add_ons_sold = frappe.db.get_all(
		"Ticket Add-on Value",
		filters={"parenttype": "Event Ticket", "parentfield": "add_ons", "parent": ["in", event_tickets]},
		fields=[{"COUNT": "*", "as": "num_add_ons_sold"}],
		pluck="num_add_ons_sold",
	)[0]

	return {
		"event": event,
		"num_tickets_sold": num_tickets_sold,
		"num_add_ons_sold": num_add_ons_sold,
		"sales": sales,
	}
