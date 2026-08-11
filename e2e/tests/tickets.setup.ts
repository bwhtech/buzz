import { test as setup } from "@playwright/test";
import {
	ADD_ON_OPTIONS,
	ADD_ON_TITLE,
	ATTENDEE_EMAIL,
	ATTENDEE_PASSWORD,
	ATTENDEE_STATE_PATH,
	TICKETS_EVENT_ROUTE,
	TICKETS_EVENT_TITLE,
} from "../data/tickets";
import { createUserWithRoles, saveLoginState } from "../helpers/auth";
import { callMethod, createDoc, deleteDoc, docExists, ensureTestTeam, getList } from "../helpers/frappe";

interface NamedDoc {
	name: string;
}

const CATEGORY = "E2E Tickets Category";
const HOST = "E2E Tickets Host";

// Event Ticket is submittable, so it has to be cancelled before it can be deleted.
async function forceDelete(request, doctype: string, name: string) {
	await callMethod(request, "frappe.client.cancel", { doctype, name }).catch(() => {});
	await deleteDoc(request, doctype, name).catch(() => {});
}

async function cleanUpPreviousRun(request) {
	const events = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { title: ["=", TICKETS_EVENT_TITLE] },
	});

	for (const event of events) {
		for (const ticket of await getList<NamedDoc>(request, "Event Ticket", {
			filters: { event: ["=", event.name] },
		})) {
			await forceDelete(request, "Event Ticket", ticket.name);
		}
		// Bookings block the event delete even though this setup no longer creates any.
		for (const booking of await getList<NamedDoc>(request, "Event Booking", {
			filters: { event: ["=", event.name] },
		})) {
			await forceDelete(request, "Event Booking", booking.name);
		}
		for (const doctype of ["Sponsorship Tier", "Event Ticket Type", "Ticket Add-on"]) {
			for (const row of await getList<NamedDoc>(request, doctype, {
				filters: { event: ["=", event.name] },
			})) {
				await deleteDoc(request, doctype, row.name).catch(() => {});
			}
		}
		await deleteDoc(request, "Buzz Event", event.name).catch(() => {});
	}
}

setup("seed a ticket owned by the attendee", async ({ request, baseURL }) => {
	await cleanUpPreviousRun(request);

	if (!(await docExists(request, "Event Category", CATEGORY))) {
		await createDoc(request, "Event Category", {
			name: CATEGORY,
			enabled: 1,
			slug: "e2e-tickets-category",
		});
	}
	const team = await ensureTestTeam(request);

	if (!(await docExists(request, "Event Host", HOST))) {
		await createDoc(request, "Event Host", { name: HOST, team });
	}

	// Far enough out that every action window (transfer, add-ons, cancellation) is open.
	const startDate = new Date();
	startDate.setDate(startDate.getDate() + 60);

	const event = await createDoc<NamedDoc>(request, "Buzz Event", {
		team,
		title: TICKETS_EVENT_TITLE,
		category: CATEGORY,
		host: HOST,
		route: TICKETS_EVENT_ROUTE,
		start_date: startDate.toISOString().split("T")[0],
		start_time: "09:00:00",
		end_time: "17:00:00",
		medium: "In Person",
		is_published: 1,
	});

	const ticketType = await createDoc<NamedDoc>(request, "Event Ticket Type", {
		event: event.name,
		title: "Tickets E2E Ticket",
		price: 0,
		currency: "INR",
		is_published: 1,
	});

	const addOn = await createDoc<NamedDoc>(request, "Ticket Add-on", {
		event: event.name,
		title: ADD_ON_TITLE,
		user_selects_option: 1,
		options: ADD_ON_OPTIONS.join("\n"),
		price: 0,
		currency: "INR",
	});

	await createUserWithRoles(request, {
		email: ATTENDEE_EMAIL,
		firstName: "Tickets Attendee",
		password: ATTENDEE_PASSWORD,
		roles: ["Buzz User"],
	});

	const ticket = await createDoc<NamedDoc>(request, "Event Ticket", {
		event: event.name,
		ticket_type: ticketType.name,
		attendee_name: "Tickets Attendee",
		attendee_email: ATTENDEE_EMAIL,
		add_ons: [{ add_on: addOn.name, value: ADD_ON_OPTIONS[0], price: 0, currency: "INR" }],
	});

	await saveLoginState(baseURL!, {
		email: ATTENDEE_EMAIL,
		password: ATTENDEE_PASSWORD,
		statePath: ATTENDEE_STATE_PATH,
	});

	console.log(`Tickets setup complete. Event ${event.name}, ticket ${ticket.name}`);
});
