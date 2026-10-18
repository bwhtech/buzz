import { test as setup } from "@playwright/test"

import {
	HOLDS_CAPACITY,
	HOLDS_EVENT_ROUTE,
	HOLDS_EVENT_TITLE,
	HOLDS_TICKET_TITLE,
} from "../data/ticket-holds"
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

const CATEGORY = "E2E Ticket Holds Category"
const HOST = "E2E Ticket Holds Host"

// Event Ticket and Event Booking are submittable, so they are cancelled before the delete.
async function forceDelete(request, doctype: string, name: string) {
	await callMethod(request, "frappe.client.cancel", { doctype, name }).catch(() => {})
	await deleteDoc(request, doctype, name).catch(() => {})
}

async function deleteRows(request, doctype: string, event: string, cancel = false) {
	for (const row of await getList<NamedDoc>(request, doctype, {
		filters: { event: ["=", event] },
	})) {
		if (cancel) await forceDelete(request, doctype, row.name)
		else await deleteDoc(request, doctype, row.name).catch(() => {})
	}
}

async function cleanUpPreviousRun(request) {
	const events = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { title: ["=", HOLDS_EVENT_TITLE] },
	})
	for (const event of events) {
		await deleteRows(request, "Ticket Hold", event.name)
		await deleteRows(request, "Event Ticket", event.name, true)
		await deleteRows(request, "Event Booking", event.name, true)
		for (const doctype of ["Event Ticket Type", "Sponsorship Tier"]) {
			await deleteRows(request, doctype, event.name)
		}
		await deleteDoc(request, "Buzz Event", event.name).catch(() => {})
	}
}

setup("seed an event with a limited free ticket type", async ({ request }) => {
	await cleanUpPreviousRun(request)

	if (!(await docExists(request, "Event Category", CATEGORY))) {
		await createDoc(request, "Event Category", {
			name: CATEGORY,
			enabled: 1,
			slug: "e2e-ticket-holds-category",
		})
	}
	const team = await ensureTestTeam(request)
	const host = await ensureEventHost(request, HOST, team)

	const startDate = new Date()
	startDate.setDate(startDate.getDate() + 30)

	const event = await createDoc<NamedDoc>(request, "Buzz Event", {
		team,
		title: HOLDS_EVENT_TITLE,
		category: CATEGORY,
		host,
		route: HOLDS_EVENT_ROUTE,
		start_date: startDate.toISOString().split("T")[0],
		start_time: "09:00:00",
		end_time: "17:00:00",
		medium: "Online",
		is_published: 1,
	})
	await openRegistrations(request, event.name)

	await createDoc(request, "Event Ticket Type", {
		event: event.name,
		title: HOLDS_TICKET_TITLE,
		is_published: 1,
		max_tickets_available: HOLDS_CAPACITY,
	})
})
