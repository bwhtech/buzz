import { expect, test } from "@playwright/test"

import { HOLDS_CAPACITY, HOLDS_EVENT_TITLE, HOLDS_TICKET_TITLE } from "../data/ticket-holds"
import { callMethod, getList } from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const PARALLEL_REQUESTS = 25

async function seededIds(request) {
	const [event] = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { title: ["=", HOLDS_EVENT_TITLE] },
	})
	const [ticketType] = await getList<NamedDoc>(request, "Event Ticket Type", {
		filters: { event: ["=", event.name], title: ["=", HOLDS_TICKET_TITLE] },
	})
	return { event: String(event.name), ticketType: String(ticketType.name) }
}

function bookOne(request, event: string, ticketType: string, index: number) {
	return callMethod(request, "buzz.api.booking.process_booking", {
		booking: {
			event,
			attendees: [
				{ first_name: `Burst ${index}`, email: "burst@buzz.test", ticket_type: ticketType },
			],
		},
	})
}

test("parallel bookings never sell more tickets than the capacity", async ({ request }) => {
	const { event, ticketType } = await seededIds(request)

	const results = await Promise.allSettled(
		Array.from({ length: PARALLEL_REQUESTS }, (_, index) =>
			bookOne(request, event, ticketType, index),
		),
	)

	const booked = results.filter((result) => result.status === "fulfilled").length
	const tickets = await getList<NamedDoc>(request, "Event Ticket", {
		filters: { ticket_type: ["=", ticketType], docstatus: ["=", 1] },
		limit: 100,
	})
	expect(booked).toBe(HOLDS_CAPACITY)
	expect(tickets).toHaveLength(HOLDS_CAPACITY)
})
