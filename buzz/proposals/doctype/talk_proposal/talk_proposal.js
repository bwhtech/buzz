// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Talk Proposal", {
	get_email_recipients(frm, fieldname) {
		if (fieldname !== "recipients") {
			return [];
		}
		return (frm.doc.speakers || []).map((speaker) => speaker.email).filter(Boolean);
	},

	refresh(frm) {
		if (frm.doc.status != "Accepted") {
			const btn = frm.add_custom_button(__("Accept and Create Talk"), () => {
				frm.call({
					method: "create_talk",
					doc: frm.doc,
					btn,
				}).then(({ message: talk }) => {
					frm.set_value("status", "Accepted");
					frm.save();
					frm.refresh();
					frappe.set_route("Form", "Event Talk", talk.name);
				});
			});
		}
	},
});
