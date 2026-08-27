// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.query_reports["Event Add-Ons Overview"] = {
	filters: [
		{
			fieldname: "event",
			label: __("Event"),
			fieldtype: "Link",
			options: "Buzz Event",
			reqd: 1,
		},
		{
			fieldname: "add_on_type",
			label: __("Add-On Type"),
			fieldtype: "Link",
			options: "Ticket Add-on",
		},
		{
			fieldname: "add_on_value",
			label: __("Add-On Value"),
			fieldtype: "Data",
		},
	],
}
