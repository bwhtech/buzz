import { expect, test } from "@playwright/test"

import {
	ADD_ON_EVENT_TITLE,
	ATTENDEE_EMAIL,
	ATTENDEE_STATE_PATH,
	CANCELLATION_EVENT_TITLE,
	TICKETS_EVENT_TITLE,
	TRANSFER_EVENT_TITLE,
	TRANSFER_RECIPIENT_EMAIL,
} from "../data/tickets"
import { newApiContext } from "../helpers/auth"
import { getDoc, getList } from "../helpers/frappe"

interface NamedDoc {
	name: string
}

// The attendee owns the ticket; get_ticket_details refuses everyone else.
test.use({ storageState: ATTENDEE_STATE_PATH })

async function seededTicket(
	baseURL: string,
	title: string = TICKETS_EVENT_TITLE,
): Promise<{ event: string; ticket: string }> {
	// The ids are looked up as Administrator, so the lookup does not depend on the UI under test.
	const admin = await newApiContext(baseURL)
	try {
		const events = await getList<NamedDoc>(admin, "Buzz Event", {
			filters: { title: ["=", title] },
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

async function openTicketLink(page, ticketId: string) {
	const loaded = page.waitForResponse((response) => response.url().includes("get_ticket_details"), {
		timeout: 20000,
	})
	await page.goto(`/b/manage/events?ticket=${ticketId}`)
	await loaded
}

const drawer = (page, title: string = TICKETS_EVENT_TITLE) =>
	page.getByRole("dialog").filter({ hasText: title })

async function asAdministrator<T>(baseURL: string, read: (admin) => Promise<T>): Promise<T> {
	const admin = await newApiContext(baseURL)
	try {
		return await read(admin)
	} finally {
		await admin.dispose()
	}
}

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

	test("saves a changed add-on", async ({ page, baseURL }) => {
		const { ticket } = await seededTicket(baseURL!, ADD_ON_EVENT_TITLE)
		await openTicketLink(page, ticket)

		await drawer(page, ADD_ON_EVENT_TITLE).getByRole("button", { name: "Add-ons" }).click()
		const dialog = page.getByRole("dialog").filter({ hasText: "Update Add-on Preferences" })
		await dialog.getByRole("combobox").click()
		await page.getByRole("option", { name: "Non-veg" }).click()
		await dialog.getByRole("button", { name: "Save Preferences" }).click()

		await expect(page.getByText("Add-on preferences updated successfully!")).toBeVisible()
		await expect(dialog).toBeHidden()
		const saved = await asAdministrator(baseURL!, (admin) =>
			getDoc<any>(admin, "Event Ticket", ticket),
		)
		expect(saved.add_ons[0].value).toBe("Non-veg")
	})

	test("transfers a ticket to a new attendee", async ({ page, baseURL }) => {
		const { ticket } = await seededTicket(baseURL!, TRANSFER_EVENT_TITLE)
		await openTicketLink(page, ticket)

		await drawer(page, TRANSFER_EVENT_TITLE).getByRole("button", { name: "Transfer" }).click()
		const dialog = page.getByRole("dialog").filter({ hasText: "New Attendee Email" })
		await dialog.getByPlaceholder("Enter first name").fill("Recipient")
		await dialog.getByPlaceholder("Enter email address").fill(TRANSFER_RECIPIENT_EMAIL)
		await dialog.getByRole("button", { name: "Transfer Ticket" }).click()

		await expect(page.getByText("Ticket transferred successfully!")).toBeVisible()
		const transferred = await asAdministrator(baseURL!, (admin) =>
			getDoc<any>(admin, "Event Ticket", ticket),
		)
		expect(transferred.attendee_email).toBe(TRANSFER_RECIPIENT_EMAIL)
		expect(transferred.attendee_email).not.toBe(ATTENDEE_EMAIL)
	})

	test("requests a cancellation from the booking receipt", async ({ page, baseURL }) => {
		const { event, ticket } = await seededTicket(baseURL!, CANCELLATION_EVENT_TITLE)
		await openTicketLink(page, ticket)

		const cancellationDrawer = drawer(page, CANCELLATION_EVENT_TITLE)
		await cancellationDrawer.getByRole("button", { name: "Request Cancellation" }).click()
		const dialog = page.getByRole("dialog").filter({ hasText: "Request Ticket Cancellation" })
		await dialog.getByText("Select All Available Tickets").click()
		await dialog.getByRole("button", { name: "Submit Cancellation Request" }).click()

		await expect(cancellationDrawer.getByText("Cancellation Requested")).toBeVisible()
		await expect(
			cancellationDrawer.getByRole("button", { name: "Request Cancellation" }),
		).toBeHidden()

		const requests = await asAdministrator(baseURL!, async (admin) => {
			const bookings = await getList<{ name: string }>(admin, "Event Booking", {
				filters: { event: ["=", event] },
			})
			return getList<{ status: string; cancel_full_booking: number }>(
				admin,
				"Ticket Cancellation Request",
				{
					fields: ["status", "cancel_full_booking"],
					filters: { booking: ["=", bookings[0].name] },
				},
			)
		})
		expect(requests).toHaveLength(1)
		expect(requests[0].status).toBe("In Review")
		expect(requests[0].cancel_full_booking).toBe(1)
	})
})
