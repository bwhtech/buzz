# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import formatdate

from buzz.booking_permissions import ensure_guests_access
from buzz.events.doctype.event_check_in_zone.event_check_in_zone import default_zone


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	event = filters.get("event")
	ensure_guests_access(event)
	if not event:
		return [], []

	zone = filters.get("zone") or default_zone(event)
	check_in_dates = get_check_in_dates(event, zone)

	columns = get_columns(check_in_dates)
	data = get_data(event, zone, check_in_dates)
	chart = get_chart(data, check_in_dates)
	report_summary = get_report_summary(data, check_in_dates)

	return columns, data, None, chart, report_summary


def get_check_in_dates(event: str, zone: str) -> list:
	"""Get all unique check-in dates for the event at the zone, sorted chronologically."""
	dates = frappe.db.sql(
		"""
		SELECT DISTINCT date
		FROM `tabEvent Check In`
		WHERE event = %s AND zone = %s AND docstatus = 1 AND date IS NOT NULL
		ORDER BY date ASC
		""",
		(event, zone),
		as_dict=True,
	)
	return [d.date for d in dates]


def get_columns(check_in_dates: list) -> list[dict]:
	"""Return columns for the report.

	One field definition per column, just like a DocType field definition.
	Dynamic columns are added for each check-in date.
	"""
	columns = [
		{
			"label": _("Ticket"),
			"fieldtype": "Link",
			"options": "Event Ticket",
			"fieldname": "ticket",
			"width": 120,
		},
		{
			"label": _("Attendee Name"),
			"fieldtype": "Data",
			"fieldname": "attendee_name",
			"width": 180,
		},
		{
			"label": _("Attendee Email"),
			"fieldtype": "Data",
			"fieldname": "attendee_email",
			"width": 200,
		},
		{
			"label": _("Ticket Type"),
			"fieldtype": "Link",
			"options": "Event Ticket Type",
			"fieldname": "ticket_type",
			"width": 150,
		},
	]

	# Add dynamic columns for each check-in date
	for i, date in enumerate(check_in_dates):
		columns.append(
			{
				"label": formatdate(date, "d MMM"),  # e.g., "12 Dec"
				"fieldtype": "Check",
				"fieldname": f"day_{i}",
				"width": 80,
			}
		)

	return columns


def get_data(event: str, zone: str, check_in_dates: list) -> list[dict]:
	"""Return data for the report.

	Shows each ticket with check-in status for each day.
	"""
	# Get all check-ins for this event
	check_ins = frappe.get_all(
		"Event Check In",
		filters={"event": event, "zone": zone, "docstatus": 1},
		fields=["ticket", "date"],
	)

	if not check_ins:
		return []

	# Build a map of ticket -> set of dates checked in
	ticket_dates = {}
	for ci in check_ins:
		if ci.ticket not in ticket_dates:
			ticket_dates[ci.ticket] = set()
		if ci.date:
			ticket_dates[ci.ticket].add(ci.date)

	# Get ticket details
	tickets = frappe.get_all(
		"Event Ticket",
		filters={"name": ["in", list(ticket_dates.keys())]},
		fields=["name", "attendee_name", "attendee_email", "ticket_type"],
	)

	# Build the data rows
	data = []
	for ticket in tickets:
		row = {
			"ticket": ticket.name,
			"attendee_name": ticket.attendee_name,
			"attendee_email": ticket.attendee_email,
			"ticket_type": ticket.ticket_type,
		}

		# Add check-in status for each date (1 or 0 for Check fieldtype)
		checked_in_dates = ticket_dates.get(ticket.name, set())
		for i, date in enumerate(check_in_dates):
			row[f"day_{i}"] = 1 if date in checked_in_dates else 0

		data.append(row)

	# Sort by attendee name
	data.sort(key=lambda x: (x.get("attendee_name") or "").lower())

	return data


def get_chart(data: list[dict], check_in_dates: list) -> dict:
	"""Return chart data showing attendance per day."""
	if not data or not check_in_dates:
		return {}

	labels = []
	values = []

	for i, date in enumerate(check_in_dates):
		labels.append(formatdate(date, "d MMM"))
		day_count = sum(1 for row in data if row.get(f"day_{i}") == 1)
		values.append(day_count)

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Attendees"), "values": values}],
		},
		"type": "bar",
		"colors": ["#4F46E5"],
	}


def get_report_summary(data: list[dict], check_in_dates: list) -> list[dict]:
	"""Return report summary with attendance counts per day and total unique attendees."""
	if not data:
		return []

	summary = []

	# Count attendance for each day
	for i, date in enumerate(check_in_dates):
		day_count = sum(1 for row in data if row.get(f"day_{i}") == 1)
		summary.append(
			{
				"value": day_count,
				"label": formatdate(date, "d MMM YYYY"),
				"datatype": "Int",
				"indicator": "blue",
			}
		)

	# Total unique attendees (anyone who attended at least one day)
	total_unique = len(data)
	summary.append(
		{
			"value": total_unique,
			"label": _("Total Unique Attendees"),
			"datatype": "Int",
			"indicator": "green",
		}
	)

	return summary
