// Copyright (c) 2026, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Buzz Schedule", {
	setup(frm) {
		frm.set_query("track", "items", (doc) => ({ filters: { schedule: doc.name } }))
	},
})
