// Copyright (c) 2026, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Event Check-in Zone", {
	refresh(frm) {
		frm.set_query("ticket_type", "ticket_types", () => {
			return {
				filters: {
					event: frm.doc.event,
				},
			}
		})
	},
})
