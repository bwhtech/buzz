// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

frappe.ui.form.on("Buzz Coupon Code", {
	refresh(frm) {
		frm.set_query("ticket_type", () => {
			return {
				filters: {
					event: frm.doc.event,
				},
			}
		})

		frm.set_query("add_on", "free_add_ons", () => {
			return {
				filters: {
					event: frm.doc.event,
				},
			}
		})

		frm.trigger("coupon_type")
		frm.trigger("applies_to")
	},

	coupon_type(frm) {
		if (frm.doc.coupon_type === "Free Tickets") {
			frm.set_value("applies_to", "Event")
		}
	},

	applies_to(frm) {
		if (frm.doc.applies_to === "Event") {
			frm.set_value("event_category", null)
		} else if (frm.doc.applies_to === "Event Category") {
			frm.set_value("event", null)
		} else {
			frm.set_value("event", null)
			frm.set_value("event_category", null)
		}
	},
})
