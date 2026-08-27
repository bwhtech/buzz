// Copyright (c) 2026, BWH Studios and contributors
// For license information, please see license.txt

// Owner is absent on purpose — it is granted at team creation and never moves.
const ASSIGNABLE_ROLES = ["Admin", "Manager", "Frontdesk", "Viewer"]

frappe.ui.form.on("Buzz Team", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.__onload?.can_manage_members) return

		frm.add_custom_button(__("Add Team Members"), () => pick_users(frm))
	},
})

function pick_users(frm, picked = []) {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Team Members"),
		fields: [
			{
				fieldname: "users",
				label: __("Users"),
				fieldtype: "MultiSelectPills",
				reqd: 1,
				// Not frappe.db.get_link_options: its standard query for User hides website
				// users and never matches a full name.
				get_data: (txt) =>
					frm.call("search_addable_users", { txt }).then(({ message }) => {
						// The control means to hide what is already picked but discards its own
						// filter() result, so clicking such a row does nothing.
						const chosen = dialog.get_value("users") || []
						return message.filter((row) => !chosen.includes(row.value))
					}),
			},
		],
		primary_action_label: __("Next"),
		primary_action({ users }) {
			if (!users?.length) return
			dialog.hide()
			set_roles(frm, users)
		},
	})
	dialog.show()
	if (picked.length) dialog.set_value("users", picked)
}

function set_roles(frm, users) {
	const dialog = new frappe.ui.Dialog({
		title: __("Set Team Roles"),
		// Keyed by position — an email is not a valid fieldname.
		fields: users.map((user, index) => ({
			fieldname: `role_${index}`,
			label: user,
			fieldtype: "Select",
			options: ASSIGNABLE_ROLES.join("\n"),
			default: "Manager",
			reqd: 1,
		})),
		secondary_action_label: __("Back"),
		secondary_action() {
			dialog.hide()
			pick_users(frm, users)
		},
		primary_action_label: __("Add Members"),
		primary_action(values) {
			const members = users.map((user, index) => ({
				user,
				team_role: values[`role_${index}`],
			}))
			frm
				.call({
					method: "add_members",
					doc: frm.doc,
					args: { members: JSON.stringify(members) },
					freeze: true,
					freeze_message: __("Adding members..."),
				})
				.then(({ message: added }) => {
					dialog.hide()
					frappe.show_alert({
						message: __("{0} member(s) added.", [added]),
						indicator: "green",
					})
					frm.reload_doc()
				})
		},
	})
	dialog.show()
}
