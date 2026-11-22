// Copyright (c) 2026, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hosted Payout", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Payments"), () => frm.trigger("get_payments"))
		}
	},

	async get_payments(frm) {
		if (!frm.doc.team || !frm.doc.from_date || !frm.doc.to_date) {
			frappe.msgprint(__("Set the Team, From Date and To Date first."))
			return
		}
		await frm.call({ method: "get_payments", doc: frm.doc, freeze: true })
		frm.dirty()
		frm.refresh()
	},
})
