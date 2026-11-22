// Copyright (c) 2026, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hosted Payment", {
	refresh(frm) {
		if (frm.doc.ping_status === "Failed" && frappe.user.has_role("System Manager")) {
			frm.add_custom_button(__("Ping Site Again"), () =>
				frm.call("ping_site_again").then(() => frm.reload_doc()),
			)
		}
	},
})
