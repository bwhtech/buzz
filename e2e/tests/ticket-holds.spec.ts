import { expect, test } from "@playwright/test"

import {
	HOLDS_CAPACITY,
	HOLDS_EVENT_ROUTE,
	HOLDS_EVENT_TITLE,
	HOLDS_TICKET_TITLE,
} from "../data/ticket-holds"
import { callMethod, createDoc, getList, updateDoc } from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const PARALLEL_REQUESTS = 25
const HELD_TEXT = "Your tickets are held for"

async function eventName(request): Promise<string> {
	const [event] = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { title: ["=", HOLDS_EVENT_TITLE] },
	})
	return String(event.name)
}

async function seededTicketType(request, event: string): Promise<string> {
	const [ticketType] = await getList<NamedDoc>(request, "Event Ticket Type", {
		filters: { event: ["=", event], title: ["=", HOLDS_TICKET_TITLE] },
	})
	return String(ticketType.name)
}

// The only published ticket type of the event, so the booking form picks it by default.
async function soleTicketType(request, event: string, title: string, capacity: number) {
	for (const row of await getList<NamedDoc>(request, "Event Ticket Type", {
		filters: { event: ["=", event] },
	})) {
		await updateDoc(request, "Event Ticket Type", row.name, { is_published: 0 })
	}
	const ticketType = await createDoc<NamedDoc>(request, "Event Ticket Type", {
		event,
		title,
		is_published: 1,
		max_tickets_available: capacity,
	})
	return String(ticketType.name)
}

async function heldQuantity(request, ticketType: string): Promise<number> {
	const holds = await getList<{ quantity: number }>(request, "Ticket Hold", {
		fields: ["quantity"],
		filters: { ticket_type: ["=", ticketType] },
		limit: 100,
	})
	return holds.reduce((total, hold) => total + hold.quantity, 0)
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

function inParallel<T>(call: (index: number) => Promise<T>) {
	return Promise.allSettled(Array.from({ length: PARALLEL_REQUESTS }, (_, index) => call(index)))
}

function fulfilled(results: PromiseSettledResult<unknown>[]) {
	return results.filter((result) => result.status === "fulfilled").length
}

test("parallel bookings never sell more tickets than the capacity", async ({ request }) => {
	const event = await eventName(request)
	const ticketType = await seededTicketType(request, event)

	const results = await inParallel((index) => bookOne(request, event, ticketType, index))

	const tickets = await getList<NamedDoc>(request, "Event Ticket", {
		filters: { ticket_type: ["=", ticketType], docstatus: ["=", 1] },
		limit: 100,
	})
	expect(fulfilled(results)).toBe(HOLDS_CAPACITY)
	expect(tickets).toHaveLength(HOLDS_CAPACITY)
})

test("parallel holds never hold more tickets than the capacity", async ({ request }) => {
	const event = await eventName(request)
	const ticketType = await soleTicketType(request, event, "Burst Hold Ticket", HOLDS_CAPACITY)

	const results = await inParallel(() =>
		callMethod(request, "buzz.api.booking.hold_tickets", {
			event,
			quantities: { [ticketType]: 1 },
		}),
	)

	expect(fulfilled(results)).toBe(HOLDS_CAPACITY)
	expect(await heldQuantity(request, ticketType)).toBe(HOLDS_CAPACITY)
})

test.describe("booking form", () => {
	let ticketType: string

	test.beforeEach(async ({ request }) => {
		const event = await eventName(request)
		ticketType = await soleTicketType(request, event, `Form Ticket ${Date.now()}`, 5)
	})

	test("holds the picked tickets and releases them on leaving", async ({ page, request }) => {
		await page.goto(`/b/register/${HOLDS_EVENT_ROUTE}`)
		await expect(page.getByText(HELD_TEXT)).toBeVisible()
		await expect.poll(() => heldQuantity(request, ticketType)).toBe(1)

		await page.getByRole("button", { name: "Add Another Attendee" }).click()
		await page.getByRole("button", { name: "Add Another Attendee" }).click()
		await expect.poll(() => heldQuantity(request, ticketType)).toBe(3)

		await page.goto("about:blank")
		await expect.poll(() => heldQuantity(request, ticketType)).toBe(0)
	})

	test("shows an expired hold and holds again", async ({ page }) => {
		await page.clock.install()
		await page.goto(`/b/register/${HOLDS_EVENT_ROUTE}`)
		await expect(page.getByText(HELD_TEXT)).toBeVisible()

		await page.clock.fastForward("10:01")
		await expect(page.getByText("Your hold has expired")).toBeVisible()

		await page.getByRole("button", { name: "Hold again" }).click()
		await expect(page.getByText(HELD_TEXT)).toBeVisible()
	})

	test("a booking turns the hold into a ticket", async ({ page, request }) => {
		await page.goto(`/b/register/${HOLDS_EVENT_ROUTE}`)
		await expect(page.getByText(HELD_TEXT)).toBeVisible()

		await page.locator('button[type="submit"]').click()
		await page.waitForURL(/booking/)

		const tickets = await getList<NamedDoc>(request, "Event Ticket", {
			filters: { ticket_type: ["=", ticketType], docstatus: ["=", 1] },
		})
		expect(tickets).toHaveLength(1)
		expect(await heldQuantity(request, ticketType)).toBe(0)
	})
})
