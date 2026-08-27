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
	],
}
