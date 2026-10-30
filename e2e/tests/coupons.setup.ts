import { test as setup } from "@playwright/test"

import {
	ACCESS_CODE,
	AUTOMATIC_OFFER_TITLE,
	COUPON_EVENT_ROUTE,
	COUPON_EVENT_TITLE,
	HIDDEN_TICKET_TITLE,
} from "../data/coupons"
import {
	callMethod,
	createDoc,
	deleteDoc,
	docExists,
	ensureEventHost,
	ensureTestTeam,
	getList,
	openRegistrations,
} from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const CATEGORY = "E2E Coupons Category"
const HOST = "E2E Coupons Host"

// Event Ticket and Event Booking are submittable, so they are cancelled before the delete.
async function forceDelete(request, doctype: string, name: string) {
	await callMethod(request, "frappe.client.cancel", { doctype, name }).catch(() => {})
	await deleteDoc(request, doctype, name).catch(() => {})
}

async function cleanUpPreviousRun(request) {
	const events = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { route: ["=", COUPON_EVENT_ROUTE] },
	})
	for (const event of events) {
		for (const doctype of ["Event Ticket", "Event Booking"]) {
			const rows = await getList<NamedDoc>(request, doctype, {
				filters: { event: ["=", event.name] },
			})
			for (const row of rows) await forceDelete(request, doctype, row.name)
		}
		for (const doctype of ["Buzz Coupon Code", "Event Ticket Type", "Sponsorship Tier"]) {
			const rows = await getList<NamedDoc>(request, doctype, {
				filters: { event: ["=", event.name] },
			})
			for (const row of rows) await deleteDoc(request, doctype, row.name).catch(() => {})
		}
		await deleteDoc(request, "Buzz Event", event.name)
	}
}

function percentageCoupon(event: string, fields: Record<string, unknown>) {
	return {
		event,
		discount_type: "Percentage",
		applies_to_all_ticket_types: 1,
		enabled: 1,
		...fields,
	}
}

setup(
	"seed an event with an automatic coupon, a promo code and an access code",
	async ({ request }) => {
		await cleanUpPreviousRun(request)

		if (!(await docExists(request, "Event Category", CATEGORY))) {
			await createDoc(request, "Event Category", {
				name: CATEGORY,
				enabled: 1,
				slug: "e2e-coupons",
			})
		}
		const team = await ensureTestTeam(request)
		const host = await ensureEventHost(request, HOST, team)

		const startDate = new Date()
		startDate.setMonth(startDate.getMonth() + 1)
		const event = await createDoc<NamedDoc>(request, "Buzz Event", {
			team,
			title: COUPON_EVENT_TITLE,
			category: CATEGORY,
			host,
			start_date: startDate.toISOString().split("T")[0],
			start_time: "09:00:00",
			end_time: "17:00:00",
			route: COUPON_EVENT_ROUTE,
			is_published: 1,
			medium: "In Person",
		})
		await openRegistrations(request, event.name)

		await createDoc(request, "Event Ticket Type", {
			event: event.name,
			title: "Standard Ticket",
			prices: [{ currency: "INR", price: 1000 }],
			is_published: 1,
		})
		await createDoc(
			request,
			"Buzz Coupon Code",
			percentageCoupon(event.name, {
				coupon_type: "Automatic",
				code: AUTOMATIC_OFFER_TITLE,
				discount_percentage: 10,
			}),
		)
		await createDoc(
			request,
			"Buzz Coupon Code",
			percentageCoupon(event.name, {
				coupon_type: "Promo Code",
				code: "E2EPROMO",
				discount_percentage: 5,
			}),
		)

		const hiddenTicketType = await createDoc<NamedDoc>(request, "Event Ticket Type", {
			event: event.name,
			title: HIDDEN_TICKET_TITLE,
			is_published: 1,
			is_hidden: 1,
		})
		await createDoc(request, "Buzz Coupon Code", {
			event: event.name,
			coupon_type: "Access Code",
			code: ACCESS_CODE,
			discount_type: "None",
			ticket_types: [{ ticket_type: hiddenTicketType.name }],
			enabled: 1,
		})
	},
)
