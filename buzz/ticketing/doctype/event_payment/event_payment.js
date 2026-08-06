// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Event Payment", {
	refresh(frm) {
		if (
			frm.doc.payment_gateway === "Razorpay" &&
			frm.doc.payment_received &&
			frm.doc.refund_status !== "Refunded"
		) {
			frm.add_custom_button(__("Refund"), () => show_refund_dialog(frm));
		}

		if (frm.doc.refund_status === "Refund Pending") {
			frm.add_custom_button(__("Sync Refund Status"), async () => {
				const status = await frm.call("sync_refund_status");
				frappe.show_alert({
					message: __("Refund Status: {0}", [status.message]),
					indicator: "green",
				});
				frm.reload_doc();
			});
		}
	},
});

function show_refund_dialog(frm) {
	const refundable_amount = frm.doc.amount - frm.doc.refunded_amount;

	const dialog = new frappe.ui.Dialog({
		title: __("Refund Payment"),
		fields: [
			{
				fieldname: "amount",
				fieldtype: "Currency",
				label: __("Refund Amount"),
				options: frm.doc.currency,
				default: refundable_amount,
				reqd: 1,
				description: __("Maximum refundable: {0}", [
					format_currency(refundable_amount, frm.doc.currency),
				]),
			},
		],
		primary_action_label: __("Refund"),
		async primary_action({ amount }) {
			dialog.hide();
			const status = await frm.call("refund", { amount });
			frappe.show_alert({
				message: __("Refund Status: {0}", [status.message]),
				indicator: "green",
			});
			frm.reload_doc();
		},
	});

	dialog.show();
}
