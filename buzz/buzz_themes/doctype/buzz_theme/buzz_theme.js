// Copyright (c) 2026, hussain@buildwithhussain.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Buzz Theme", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.theme_settings) {
			return;
		}

		const settings_doctype_name = `${frm.doc.theme_name} Settings`;
		frappe.db.exists("DocType", settings_doctype_name).then((exists) => {
			if (exists) {
				frm.dashboard.add_comment(
					__("DocType {0} already exists. Link it in the Theme Settings field.", [
						settings_doctype_name,
					]),
					"yellow",
					true
				);
				return;
			}

			frm.add_custom_button(__("Scaffold Theme Settings"), () => {
				frappe.confirm(
					__("This will create a new DocType named {0}. Continue?", [
						settings_doctype_name,
					]),
					() => {
						frm.call("scaffold_theme_settings").then((response) => {
							if (response.message) {
								frappe.show_alert({
									message: __("Created {0}", [response.message]),
									indicator: "green",
								});
								frm.reload_doc();
							}
						});
					}
				);
			});
		});
	},
});
