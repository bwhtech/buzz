import { type APIRequestContext, test as setup } from "@playwright/test"

import {
	APPROVAL_EVENT_ROUTE,
	APPROVAL_EVENT_TITLE,
	APPROVAL_TICKET_TITLE,
	REQUESTER_PASSWORD,
	REQUESTERS,
} from "../data/approval-registration"
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

const CATEGORY = "E2E Approval Category"
const HOST = "E2E Approval Host"

// Bookings and tickets are submittable, so they are cancelled before they are deleted.
async function forceDelete(request: APIRequestContext, doctype: string, name: string) {
	await callMethod(request, "frappe.client.cancel", { doctype, name }).catch(() => {})
	await deleteDoc(request, doctype, name).catch(() => {})
}

async function cleanUpPreviousRun(request: APIRequestContext) {
	const events = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { title: ["=", APPROVAL_EVENT_TITLE] },
	})

	for (const event of events) {
		for (const doctype of ["Event Ticket", "Event Booking"]) {
			for (const row of await getList<NamedDoc>(request, doctype, {
				filters: { event: ["=", event.name] },
			})) {
				await forceDelete(request, doctype, row.name)
			}
		}
		for (const doctype of ["Sponsorship Tier", "Event Ticket Type", "Ticket Add-on"]) {
			for (const row of await getList<NamedDoc>(request, doctype, {
				filters: { event: ["=", event.name] },
			})) {
				await deleteDoc(request, doctype, row.name).catch(() => {})
			}
		}
		await deleteDoc(request, "Buzz Event", event.name).catch(() => {})
	}
}

setup("seed a free event and its requesters", async ({ request, baseURL }) => {
	await cleanUpPreviousRun(request)

	if (!(await docExists(request, "Event Category", CATEGORY))) {
		await createDoc(request, "Event Category", {
			name: CATEGORY,
			enabled: 1,
			slug: "e2e-approval-category",
		})
	}
	const team = await ensureTestTeam(request)
	const host = await ensureEventHost(request, HOST, team)

	const startDate = new Date()
	startDate.setDate(startDate.getDate() + 60)

	const event = await createDoc<NamedDoc>(request, "Buzz Event", {
		team,
		title: APPROVAL_EVENT_TITLE,
		category: CATEGORY,
		host,
		route: APPROVAL_EVENT_ROUTE,
		start_date: startDate.toISOString().split("T")[0],
		start_time: "09:00:00",
		end_time: "17:00:00",
		medium: "In Person",
		is_published: 1,
	})
	await openRegistrations(request, event.name)

	// Free, with approval left off: the spec turns it on from the Registration page.
	await createDoc(request, "Event Ticket Type", {
		event: event.name,
		title: APPROVAL_TICKET_TITLE,
		is_published: 1,
	})

	for (const requester of Object.values(REQUESTERS)) {
		await createUserWithRoles(request, {
			email: requester.email,
			firstName: requester.name,
			password: REQUESTER_PASSWORD,
			roles: ["Buzz User"],
		})
		await saveLoginState(baseURL!, {
			email: requester.email,
			password: REQUESTER_PASSWORD,
			statePath: requester.statePath,
		})
	}
})
