// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Event Booking", {
	refresh(frm) {
		frm.set_query("ticket_type", "attendees", (doc, cdt, cdn) => {
			return {
				filters: {
					event: doc.event,
				},
			};
		});

		// Add Approve/Reject buttons for pending bookings
		if (frappe.user.has_role("Event Manager") && frm.doc.status === "Approval Pending") {
			frm.add_custom_button(__("Approve and Submit"), function () {
				frappe.confirm("Are you sure you want to approve this booking?", function () {
					frm.call("approve_booking").then(() => {
						frm.refresh();
					});
				});
			});

			frm.add_custom_button(__("Reject"), function () {
				frappe.confirm("Are you sure you want to reject this booking?", function () {
					frm.call("reject_booking").then(() => {
						frm.refresh();
					});
				});
			});
		}

		if (
			frappe.user.has_role("System Manager") &&
			frm.doc.docstatus === 1 &&
			frm.doc.payment_status === "Paid" &&
			frm.doc.refund_status !== "Refunded"
		) {
			frm.add_custom_button(__("Refund"), () => showRefundDialog(frm));
		}
	},
});

async function showRefundDialog(frm) {
	const { message: tickets = [] } = await frm.call("get_refundable_tickets");
	const refundable = flt(frm.doc.total_amount) - flt(frm.doc.refunded_amount);

	const sumOf = (selected) =>
		tickets
			.filter((ticket) => selected.includes(ticket.ticket))
			.reduce((total, ticket) => total + flt(ticket.amount), 0);

	const dialog = new frappe.ui.Dialog({
		title: __("Refund Booking"),
		fields: [
			{
				fieldname: "tickets",
				fieldtype: "MultiCheck",
				label: __("Tickets"),
				columns: 1,
				select_all: true,
				options: tickets.map((ticket) => ({
					label: `${ticket.attendee} — ${format_currency(
						ticket.amount,
						frm.doc.currency
					)}`,
					value: ticket.ticket,
				})),
				on_change: () => {
					dialog.set_value("amount", sumOf(dialog.get_value("tickets") || []));
				},
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "amount",
				fieldtype: "Currency",
				label: __("Refund Amount"),
				options: frm.doc.currency,
				reqd: 1,
				description: __(
					"Refundable: {0}. Tick tickets to cancel them along with the refund, or leave them unticked and type an amount to refund money only.",
					[format_currency(refundable, frm.doc.currency)]
				),
			},
		],
		primary_action_label: __("Refund"),
		primary_action({ amount, tickets: selected = [] }) {
			const question = selected.length
				? __("Refund {0} and queue {1} ticket(s) for cancellation?", [
						format_currency(amount, frm.doc.currency),
						selected.length,
				  ])
				: __("Refund {0}? No tickets will be cancelled.", [
						format_currency(amount, frm.doc.currency),
				  ]);

			frappe.confirm(question, async () => {
				dialog.hide();
				frappe.show_alert({
					message: __("Sending the refund to Razorpay..."),
					indicator: "blue",
				});

				await frm.call("refund", { amount, tickets: selected });

				frappe.show_alert({
					message: selected.length
						? __(
								"Refund initiated. Razorpay confirms it separately, and the tickets are queued for cancellation review."
						  )
						: __("Refund initiated. Razorpay confirms it separately."),
					indicator: "green",
				});
				frm.reload_doc();
			});
		},
	});

	dialog.show();
}
