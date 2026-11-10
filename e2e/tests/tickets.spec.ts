import { expect, test } from "@playwright/test"

import { ADD_ON_TITLE, ATTENDEE_STATE_PATH, TICKETS_EVENT_TITLE } from "../data/tickets"
import { newApiContext } from "../helpers/auth"
import { getList } from "../helpers/frappe"

interface NamedDoc {
	name: string
}

interface TicketDetails {
	can_transfer_ticket: unknown
	can_change_add_ons: unknown
	can_request_cancellation: unknown
	add_ons: Array<{ title: string; value: string; options: string[] }>
}

// The attendee owns the ticket; get_ticket_details refuses everyone else.
test.use({ storageState: ATTENDEE_STATE_PATH })

async function seededTicket(baseURL: string): Promise<{ event: string; ticket: string }> {
	// The ids are looked up as Administrator, so the lookup does not depend on the UI under test.
	const admin = await newApiContext(baseURL)
	try {
		const events = await getList<NamedDoc>(admin, "Buzz Event", {
			filters: { title: ["=", TICKETS_EVENT_TITLE] },
		})
		expect(events.length).toBeGreaterThan(0)

		const tickets = await getList<NamedDoc>(admin, "Event Ticket", {
			filters: { event: ["=", events[0].name] },
		})
		expect(tickets.length).toBeGreaterThan(0)
		return { event: String(events[0].name), ticket: tickets[0].name }
	} finally {
		await admin.dispose()
	}
}

/** Opens the drawer from a ticket link, returning the details payload the drawer fetched. */
async function openTicketLink(page, ticketId: string): Promise<TicketDetails> {
	const pending = page.waitForResponse(
		(response) => response.url().includes("get_ticket_details"),
		{ timeout: 20000 },
	)
	await page.goto(`/b/manage/events?ticket=${ticketId}`)
	const body = await (await pending).json()
	return body.data as TicketDetails
}

const drawer = (page) => page.getByRole("dialog").filter({ hasText: TICKETS_EVENT_TITLE })

test.describe("Event drawer tickets", () => {
	test("a ticket link opens the drawer on its event", async ({ page, baseURL }) => {
		const { ticket } = await seededTicket(baseURL!)
		await openTicketLink(page, ticket)

		await expect(drawer(page).getByText("You're in")).toBeVisible({ timeout: 15000 })
		await expect(drawer(page).getByRole("button", { name: "Ticket QR" })).toBeVisible()
		await expect(page).not.toHaveURL(/ticket=/)
	})

	test("an event link opens the drawer", async ({ page, baseURL }) => {
		const { event } = await seededTicket(baseURL!)
		await page.goto(`/b/manage/events?event=${event}`)

		await expect(drawer(page).getByText("You're in")).toBeVisible({ timeout: 15000 })
	})

	test("reports the action windows as plain booleans", async ({ page, baseURL }) => {
		const details = await openTicketLink(page, (await seededTicket(baseURL!)).ticket)

		// The event is seeded 60 days out, so every window is open.
		expect(details.can_transfer_ticket).toBe(true)
		expect(details.can_change_add_ons).toBe(true)
		expect(details.can_request_cancellation).toBe(true)
	})

	test("carries the add-on with its selectable options", async ({ page, baseURL }) => {
		const details = await openTicketLink(page, (await seededTicket(baseURL!)).ticket)

		expect(details.add_ons).toHaveLength(1)
		expect(details.add_ons[0].title).toBe(ADD_ON_TITLE)
		expect(details.add_ons[0].value).toBe("Veg")
		expect(details.add_ons[0].options).toEqual(["Veg", "Non-veg"])
	})

	test("offers transfer and add-on changes while their windows are open", async ({
		page,
		baseURL,
	}) => {
		await openTicketLink(page, (await seededTicket(baseURL!)).ticket)

		await drawer(page).getByRole("button", { name: "Add-ons" }).click()
		const addOnDialog = page.getByRole("dialog").filter({ hasText: "Update Add-on Preferences" })
		await expect(addOnDialog.getByText(ADD_ON_TITLE)).toBeVisible()
		await addOnDialog.getByRole("button", { name: "Cancel" }).click()

		await drawer(page).getByRole("button", { name: "Transfer" }).click()
		const transferDialog = page.getByRole("dialog").filter({ hasText: "New Attendee Email" })
		await expect(transferDialog).toBeVisible()
	})
})
