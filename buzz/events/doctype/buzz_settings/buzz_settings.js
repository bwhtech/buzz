// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Buzz Settings", {
	refresh(frm) {
		if (!frm.doc.list_on_buzz_events || frm.is_dirty()) return
		frm.add_custom_button(__("Sync Events"), () => {
			frm.call("sync_events").then(() => {
				frappe.show_alert({
					message: __("Syncing upcoming events to buzz.events"),
					indicator: "green",
				})
			})
		})
	},
})
