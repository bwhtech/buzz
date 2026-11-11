import { test as setup } from "@playwright/test"

import {
	ADD_ON_OPTIONS,
	ADD_ON_TITLE,
	ATTENDEE_EMAIL,
	ATTENDEE_PASSWORD,
	ATTENDEE_STATE_PATH,
	ADD_ON_EVENT_TITLE,
	CANCELLATION_EVENT_TITLE,
	TICKETS_EVENT_ROUTE,
	TICKETS_EVENT_TITLE,
	TRANSFER_EVENT_TITLE,
} from "../data/tickets"
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

const CATEGORY = "E2E Tickets Category"
const HOST = "E2E Tickets Host"

// Event Ticket is submittable, so it has to be cancelled before it can be deleted.
async function forceDelete(request, doctype: string, name: string) {
	await callMethod(request, "frappe.client.cancel", { doctype, name }).catch(() => {})
	await deleteDoc(request, doctype, name).catch(() => {})
}

const EVENTS = [
	{ title: TICKETS_EVENT_TITLE, route: TICKETS_EVENT_ROUTE },
	{ title: ADD_ON_EVENT_TITLE, route: "tickets-e2e-add-on" },
	{ title: TRANSFER_EVENT_TITLE, route: "tickets-e2e-transfer" },
	{ title: CANCELLATION_EVENT_TITLE, route: "tickets-e2e-cancellation" },
]

async function cleanUpPreviousRun(request) {
	const events = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { title: ["in", EVENTS.map((event) => event.title)] },
	})

	for (const event of events) {
		for (const ticket of await getList<NamedDoc>(request, "Event Ticket", {
			filters: { event: ["=", event.name] },
		})) {
			await forceDelete(request, "Event Ticket", ticket.name)
		}
		for (const booking of await getList<NamedDoc>(request, "Event Booking", {
			filters: { event: ["=", event.name] },
		})) {
			for (const row of await getList<NamedDoc>(request, "Ticket Cancellation Request", {
				filters: { booking: ["=", booking.name] },
			})) {
				await forceDelete(request, "Ticket Cancellation Request", row.name)
			}
		}
		for (const booking of await getList<NamedDoc>(request, "Event Booking", {
			filters: { event: ["=", event.name] },
		})) {
			await forceDelete(request, "Event Booking", booking.name)
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

interface SeededEvent {
	event: string
	ticketType: string
	addOn: string
}

async function seedEvent(request, team: string, host: string, spec: (typeof EVENTS)[number]) {
	// Far enough out that every action window (transfer, add-ons, cancellation) is open.
	const startDate = new Date()
	startDate.setDate(startDate.getDate() + 60)

	const event = await createDoc<NamedDoc>(request, "Buzz Event", {
		team,
		title: spec.title,
		category: CATEGORY,
		host,
		route: spec.route,
		start_date: startDate.toISOString().split("T")[0],
		start_time: "09:00:00",
		end_time: "17:00:00",
		medium: "In Person",
		is_published: 1,
	})
	await openRegistrations(request, event.name)

	const ticketType = await createDoc<NamedDoc>(request, "Event Ticket Type", {
		event: event.name,
		title: "Tickets E2E Ticket",
		is_published: 1,
	})
	const addOn = await createDoc<NamedDoc>(request, "Ticket Add-on", {
		event: event.name,
		title: ADD_ON_TITLE,
		user_selects_option: 1,
		options: ADD_ON_OPTIONS.join("\n"),
		price: 0,
		currency: "INR",
	})
	return { event: event.name, ticketType: ticketType.name, addOn: addOn.name }
}

function seedTicket(request, seeded: SeededEvent, email: string, name: string) {
	return createDoc<NamedDoc>(request, "Event Ticket", {
		event: seeded.event,
		ticket_type: seeded.ticketType,
		attendee_name: name,
		attendee_email: email,
		add_ons: [{ add_on: seeded.addOn, value: ADD_ON_OPTIONS[0], price: 0, currency: "INR" }],
		// The event drawer lists submitted tickets only.
		docstatus: 1,
	})
}

// A submitted booking with no price confirms on its own and issues the attendee's ticket.
function seedBooking(request, seeded: SeededEvent) {
	return createDoc<NamedDoc>(request, "Event Booking", {
		event: seeded.event,
		user: ATTENDEE_EMAIL,
		attendees: [
			{
				first_name: "Tickets",
				last_name: "Attendee",
				email: ATTENDEE_EMAIL,
				ticket_type: seeded.ticketType,
				currency: "INR",
				amount: 0,
			},
		],
		docstatus: 1,
	})
}

setup("seed tickets for the attendee", async ({ request, baseURL }) => {
	await cleanUpPreviousRun(request)

	if (!(await docExists(request, "Event Category", CATEGORY))) {
		await createDoc(request, "Event Category", {
			name: CATEGORY,
			enabled: 1,
			slug: "e2e-tickets-category",
		})
	}
	const team = await ensureTestTeam(request)
	const host = await ensureEventHost(request, HOST, team)

	await createUserWithRoles(request, {
		email: ATTENDEE_EMAIL,
		firstName: "Tickets Attendee",
		password: ATTENDEE_PASSWORD,
		roles: ["Buzz User"],
	})

	const seeded: SeededEvent[] = []
	for (const spec of EVENTS) seeded.push(await seedEvent(request, team, host, spec))
	const [mainEvent, addOnEvent, transferEvent, cancellationEvent] = seeded

	const ticket = await seedTicket(request, mainEvent, ATTENDEE_EMAIL, "Tickets Attendee")
	await seedTicket(request, addOnEvent, ATTENDEE_EMAIL, "Tickets Attendee")
	await seedTicket(request, transferEvent, ATTENDEE_EMAIL, "Tickets Attendee")
	await seedBooking(request, cancellationEvent)

	await saveLoginState(baseURL!, {
		email: ATTENDEE_EMAIL,
		password: ATTENDEE_PASSWORD,
		statePath: ATTENDEE_STATE_PATH,
	})

	console.log(`Tickets setup complete. Event ${mainEvent.event}, ticket ${ticket.name}`)
})
