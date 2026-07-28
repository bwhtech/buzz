import { test as setup, expect } from "@playwright/test";
import { createUserWithRoles, saveLoginState } from "../helpers/auth";
import { callMethod, createDoc, deleteDoc, docExists, getList } from "../helpers/frappe";
import {
	CHECK_IN_ATTENDEE_EMAIL,
	CHECK_IN_ATTENDEE_NAME,
	CHECK_IN_EVENT_ROUTE,
	CHECK_IN_EVENT_TITLE,
	FRONTDESK_EMAIL,
	FRONTDESK_PASSWORD,
	FRONTDESK_STATE_PATH,
	NO_ROLE_EMAIL,
	NO_ROLE_PASSWORD,
	NO_ROLE_STATE_PATH,
} from "../data/check-in";

interface NamedDoc {
	name: string;
}

const CATEGORY = "E2E Check-in Category";
const HOST = "E2E Check-in Host";

// Cancel-then-delete: Event Ticket and Event Check In are submittable.
async function forceDelete(request, doctype: string, name: string) {
	await callMethod(request, "frappe.client.cancel", { doctype, name }).catch(() => {});
	await deleteDoc(request, doctype, name).catch(() => {});
}

// Cleanup runs here rather than in the spec's afterAll: the spec runs under the front-desk
// storage state, and the helpers sign their writes with the Administrator CSRF token.
async function cleanUpPreviousRun(request) {
	const events = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { title: ["=", CHECK_IN_EVENT_TITLE] },
	});

	for (const event of events) {
		const tickets = await getList<NamedDoc>(request, "Event Ticket", {
			filters: { event: ["=", event.name] },
		});
		for (const ticket of tickets) {
			const checkIns = await getList<NamedDoc>(request, "Event Check In", {
				filters: { ticket: ["=", ticket.name] },
			});
			for (const checkIn of checkIns) {
				await forceDelete(request, "Event Check In", checkIn.name);
			}
			await forceDelete(request, "Event Ticket", ticket.name);
		}

		for (const doctype of ["Sponsorship Tier", "Event Ticket Type", "Ticket Add-on"]) {
			const rows = await getList<NamedDoc>(request, doctype, {
				filters: { event: ["=", event.name] },
			});
			for (const row of rows) {
				await deleteDoc(request, doctype, row.name).catch(() => {});
			}
		}

		await deleteDoc(request, "Buzz Event", event.name).catch(() => {});
	}
}

setup("seed check-in event, ticket and front-desk user", async ({ request, baseURL }) => {
	await cleanUpPreviousRun(request);

	if (!(await docExists(request, "Event Category", CATEGORY))) {
		await createDoc(request, "Event Category", {
			name: CATEGORY,
			enabled: 1,
			slug: "e2e-check-in-category",
		});
	}

	if (!(await docExists(request, "Event Host", HOST))) {
		await createDoc(request, "Event Host", { name: HOST });
	}

	const startDate = new Date();
	startDate.setDate(startDate.getDate() + 7);

	const event = await createDoc<NamedDoc>(request, "Buzz Event", {
		title: CHECK_IN_EVENT_TITLE,
		category: CATEGORY,
		host: HOST,
		route: CHECK_IN_EVENT_ROUTE,
		start_date: startDate.toISOString().split("T")[0],
		start_time: "09:00:00",
		end_time: "17:00:00",
		medium: "In Person",
		is_published: 1,
	});

	const ticketType = await createDoc<NamedDoc>(request, "Event Ticket Type", {
		event: event.name,
		title: "Check-in Ticket",
		price: 0,
		currency: "INR",
		is_published: 1,
	});

	const ticket = await createDoc<NamedDoc>(request, "Event Ticket", {
		event: event.name,
		ticket_type: ticketType.name,
		attendee_name: CHECK_IN_ATTENDEE_NAME,
		attendee_email: CHECK_IN_ATTENDEE_EMAIL,
	});
	expect(ticket.name).toBeTruthy();

	await createUserWithRoles(request, {
		email: FRONTDESK_EMAIL,
		firstName: "Frontdesk",
		password: FRONTDESK_PASSWORD,
		roles: ["Buzz User", "Frontdesk Manager"],
	});

	await saveLoginState(baseURL!, {
		email: FRONTDESK_EMAIL,
		password: FRONTDESK_PASSWORD,
		statePath: FRONTDESK_STATE_PATH,
	});

	await createUserWithRoles(request, {
		email: NO_ROLE_EMAIL,
		firstName: "No Frontdesk",
		password: NO_ROLE_PASSWORD,
		roles: ["Buzz User"],
	});

	await saveLoginState(baseURL!, {
		email: NO_ROLE_EMAIL,
		password: NO_ROLE_PASSWORD,
		statePath: NO_ROLE_STATE_PATH,
	});

	console.log(`Check-in setup complete. Event ${event.name}, ticket ${ticket.name}`);
});
