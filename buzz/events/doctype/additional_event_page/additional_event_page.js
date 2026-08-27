// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt
frappe.ui.form.on("Additional Event Page", {
	refresh(frm) {
		if (frm.doc.is_published) {
			frappe.db.get_value("Buzz Event", frm.doc.event, "route").then(({ message }) => {
				frm.add_web_link(`/events/${message.route}/${frm.doc.route}`)
			})
		}
	},
})
