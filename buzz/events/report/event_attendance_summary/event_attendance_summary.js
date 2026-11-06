// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.query_reports["Event Attendance Summary"] = {
	filters: [
		{
			fieldname: "event",
			label: __("Event"),
			fieldtype: "Link",
			options: "Buzz Event",
			reqd: 1,
		},
		{
			fieldname: "zone",
			label: __("Zone"),
			fieldtype: "Link",
			options: "Event Check-in Zone",
			description: __("Empty is the event's default zone"),
			get_query() {
				return { filters: { event: frappe.query_report.get_filter_value("event") } }
			},
		},
	],
}
