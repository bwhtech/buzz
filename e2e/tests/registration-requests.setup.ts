import { type APIRequestContext, test as setup } from "@playwright/test"

import {
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
	for (const row of rows) await forceDelete(request, doctype, row.name)
}

async function cleanUpPreviousRun(request: APIRequestContext) {
	const events = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { title: ["=", REQUESTS_EVENT_TITLE] },
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

setup("seed a free event that requires approval", async ({ request, baseURL }) => {
	await cleanUpPreviousRun(request)

	if (!(await docExists(request, "Event Category", CATEGORY))) {
		await createDoc(request, "Event Category", {
			name: CATEGORY,
			enabled: 1,
			slug: "e2e-requests-category",
		})
	}
	const team = await ensureTestTeam(request)
	const host = await ensureEventHost(request, HOST, team)

	const startDate = new Date()
	startDate.setDate(startDate.getDate() + 60)

	const event = await createDoc<NamedDoc>(request, "Buzz Event", {
		team,
		title: REQUESTS_EVENT_TITLE,
		category: CATEGORY,
		host,
		route: REQUESTS_EVENT_ROUTE,
		start_date: startDate.toISOString().split("T")[0],
		start_time: "09:00:00",
		end_time: "17:00:00",
		medium: "In Person",
		is_published: 1,
	})
	await openRegistrations(request, event.name)

	await createDoc(request, "Event Ticket Type", {
		event: event.name,
		title: REQUESTS_TICKET_TITLE,
		requires_approval: 1,
		is_published: 1,
	})

	await createUserWithRoles(request, {
		email: REQUESTER.email,
		firstName: REQUESTER.name,
		password: REQUESTER_PASSWORD,
		roles: ["Buzz User"],
	})
	await saveLoginState(baseURL!, {
		email: REQUESTER.email,
		password: REQUESTER_PASSWORD,
		statePath: REQUESTER.statePath,
	})
})
