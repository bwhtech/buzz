// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Buzz Custom Field", {
	refresh(frm) {
		frm.set_query("custom_form_doctype", function () {
			return {
				filters: {
					istable: 0,
					issingle: 0,
				},
			}
		})
	},
})
