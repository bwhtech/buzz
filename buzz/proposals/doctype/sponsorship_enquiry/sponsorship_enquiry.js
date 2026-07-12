// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sponsorship Enquiry", {
	setup(frm) {
		frm.set_query("tier", (doc) => {
			return {
				filters: {
					event: doc.event,
				},
			};
		});
	},

	event(frm) {
		if (frm.doc.tier) {
			frm.set_value("tier", null);
		}
	},

	refresh(frm) {
		if (!frm.doc.__islocal) {
			if (frm.doc.status === "Approval Pending") {
				frm.add_custom_button(__("Approve"), () => {
					frm.set_value("status", "Payment Pending");
					frm.save();
				});
			}

			frm.add_custom_button(__("Create Sponsor"), () => {
				frm.call("create_sponsor").then(() => {
					frappe.show_alert(__("Sponsor Created!"));
					frm.refresh();
				});
			});
		}
	},
});
