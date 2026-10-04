frappe.ui.form.on("Sponsor Enquiry Form", {
	async refresh(frm) {
		if (frm.is_new()) return
		const result = await frappe.db.get_value("Buzz Event", frm.doc.event, "route")
		if (!result.message?.route) return
		const url = `/b/${result.message.route}/${frm.doc.route}`
		frm.add_web_link(url, __("View Enquiry Form"))
		frm.add_custom_button(__("Copy Form Link"), () => {
			frappe.utils.copy_to_clipboard(`${window.location.origin}${url}`)
		})
	},
})
