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
			const btn = frm.add_custom_button(
				__("Accept and Create Talk"),
				() => {
					frappe.confirm(
						__(
							"This action will accept this proposal and create a talk against it. Any speakers without a Buzz account will get one."
						),
						() => {
							frm.call({
								method: "create_talk",
								doc: frm.doc,
								btn,
							}).then(({ message: talk }) => {
								frappe.show_alert({
									message: __("Talk created"),
									indicator: "green",
								});
								frappe.set_route("Form", "Event Talk", talk.name);
							});
						}
					);
				},
				__("Actions")
			);
		}
	},
});
