// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Attendee Ticket Add-on", {
// });

frappe.ui.form.on("Ticket Add-on Value", {
	add_on(frm, cdt, cdn) {
		const doc = frappe.get_doc(cdt, cdn)
		frappe.db.get_value("Ticket Add-on", doc.add_on, "options").then(({ message }) => {
			if (message.options) {
				const options = message.options.trim().split("\n")
				frm.grids[0].grid.grid_rows_by_docname[cdn].on_grid_fields_dict.value.set_data(options)
			}
		})
	},
})
