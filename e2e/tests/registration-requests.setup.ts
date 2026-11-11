import { type APIRequestContext, test as setup } from "@playwright/test"

import {
	PAID_EVENT_ROUTE,
	PAID_EVENT_TITLE,
	PAID_TICKET_TITLE,
	REQUESTER,
	REQUESTER_PASSWORD,
	REQUESTS_EVENT_ROUTE,
	REQUESTS_EVENT_TITLE,
	REQUESTS_TICKET_TITLE,
} from "../data/registration-requests"
import { createUserWithRoles, saveLoginState } from "../helpers/auth"
import {
	callMethod,
	createDoc,
	deleteDoc,
	docExists,
	ensureEventHost,
	ensureTestTeam,
	getList,
	openRegistrations,
	updateDoc,
} from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const CATEGORY = "E2E Requests Category"
const HOST = "E2E Requests Host"

// Bookings and tickets are submittable, so they are cancelled before they are deleted.
async function forceDelete(request: APIRequestContext, doctype: string, name: string) {
	await callMethod(request, "frappe.client.cancel", { doctype, name }).catch(() => {})
	await deleteDoc(request, doctype, name).catch(() => {})
}

async function deleteEventRows(request: APIRequestContext, doctype: string, event: string) {
	const rows = await getList<NamedDoc>(request, doctype, { filters: { event: ["=", event] } })
	for (const row of rows) {
		if (doctype === "Event Booking") await deletePayments(request, row.name)
		await forceDelete(request, doctype, row.name)
	}
}

// Starting a payment from the booking leaves an Event Payment that blocks its deletion.
async function deletePayments(request: APIRequestContext, booking: string) {
	const payments = await getList<NamedDoc>(request, "Event Payment", {
		filters: { reference_doctype: "Event Booking", reference_docname: booking },
	})
	for (const payment of payments) await deleteDoc(request, "Event Payment", payment.name)
}

async function cleanUpPreviousRun(request: APIRequestContext) {
	const events = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { title: ["in", [REQUESTS_EVENT_TITLE, PAID_EVENT_TITLE]] },
	})
	for (const event of events) {
		for (const doctype of [
			"Event Ticket",
			"Event Booking",
			"Sponsorship Tier",
			"Event Ticket Type",
			"Ticket Add-on",
		]) {
			await deleteEventRows(request, doctype, event.name)
		}
		await deleteDoc(request, "Buzz Event", event.name).catch(() => {})
	}
}

async function seedEvent(
	request: APIRequestContext,
	event: { title: string; route: string; ticketTitle: string; prices?: object[] },
) {
	const team = await ensureTestTeam(request)
	const host = await ensureEventHost(request, HOST, team)

	const startDate = new Date()
	startDate.setDate(startDate.getDate() + 60)

	const { name } = await createDoc<NamedDoc>(request, "Buzz Event", {
		team,
		title: event.title,
		category: CATEGORY,
		host,
		route: event.route,
		start_date: startDate.toISOString().split("T")[0],
		start_time: "09:00:00",
		end_time: "17:00:00",
		medium: "In Person",
		is_published: 1,
	})
	await openRegistrations(request, name)

	await createDoc(request, "Event Ticket Type", {
		event: name,
		title: event.ticketTitle,
		requires_approval: 1,
		is_published: 1,
		prices: event.prices,
	})
}

setup("seed events that require approval", async ({ request, baseURL }) => {
	await cleanUpPreviousRun(request)

	if (!(await docExists(request, "Event Category", CATEGORY))) {
		await createDoc(request, "Event Category", {
			name: CATEGORY,
			enabled: 1,
			slug: "e2e-requests-category",
		})
	}
	await seedEvent(request, {
		title: REQUESTS_EVENT_TITLE,
		route: REQUESTS_EVENT_ROUTE,
		ticketTitle: REQUESTS_TICKET_TITLE,
	})
	await seedEvent(request, {
		title: PAID_EVENT_TITLE,
		route: PAID_EVENT_ROUTE,
		ticketTitle: PAID_TICKET_TITLE,
		prices: [{ currency: "INR", price: 500 }],
	})

	await createUserWithRoles(request, {
		email: REQUESTER.email,
		firstName: REQUESTER.name,
		password: REQUESTER_PASSWORD,
		roles: ["Buzz User"],
	})
	// A site with onboarding on would otherwise gate the requester behind the profile step.
	await updateDoc(request, "User", REQUESTER.email, { buzz_onboarding_status: "Completed" })
	await saveLoginState(baseURL!, {
		email: REQUESTER.email,
		password: REQUESTER_PASSWORD,
		statePath: REQUESTER.statePath,
	})
})
