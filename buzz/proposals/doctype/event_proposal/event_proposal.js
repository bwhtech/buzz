// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Event Proposal", {
	// Guest submissions leave owner as "Guest", so there is nothing to prefill.
	get_email_recipients(frm, fieldname) {
		const owner = frm.doc.owner || "";
		return fieldname === "recipients" && owner.includes("@") ? [owner] : [];
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus == 0) {
			frm.set_intro("Buzz Event will be created on submission of this document", "yellow");
		}

		if (!frm.is_new() && frm.doc.docstatus == 0 && !frm.doc.host) {
			frm.add_custom_button(__("Create Host"), () => {
				frm.call("create_host").then(() => {
					frappe.show_alert(__("Host Created!"));
					frm.refresh();
				});
			});
		}
	},
});
