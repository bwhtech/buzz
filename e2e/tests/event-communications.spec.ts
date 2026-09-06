import { expect, test } from "@playwright/test"

import { createDoc, deleteDoc, getList, updateDoc } from "../helpers/frappe"

interface NamedDoc {
	name: string
}

// Runs under the shared Administrator state, against the event seeded by event.setup.ts.
test.describe("Event communications", () => {
	let event: NamedDoc
	let ticket: NamedDoc

	test.beforeEach(async ({ page, request }) => {
		;[event] = await getList<NamedDoc>(request, "Buzz Event", {
			filters: { title: ["=", "E2E Test Event"] },
		})
		const [ticketType] = await getList<NamedDoc>(request, "Event Ticket Type", {
			filters: { event: ["=", event.name] },
		})
		// A submitted ticket is what makes someone a guest; without one there is nobody to send to.
		ticket = await createDoc<NamedDoc>(request, "Event Ticket", {
			event: event.name,
			ticket_type: ticketType.name,
			attendee_name: "Comms Guest",
			attendee_email: `comms-guest-${Date.now()}@example.com`,
			docstatus: 1,
		})
		await page.goto(`/b/manage/events/${event.name}/communications`)
	})

	// Both link to the event, and event.setup.ts deletes it on the next run.
	test.afterEach(async ({ request }) => {
		const sent = await getList<NamedDoc>(request, "Event Communication", {
			filters: { event: ["=", event.name] },
		})
		for (const row of sent)
			await deleteDoc(request, "Event Communication", row.name).catch(() => {})
		await updateDoc(request, "Event Ticket", ticket.name, { docstatus: 2 }).catch(() => {})
		await deleteDoc(request, "Event Ticket", ticket.name).catch(() => {})
	})

	test("sends a message to the guests and lists it", async ({ page }) => {
		const text = `Doors open at nine ${Date.now()}`
		await page.getByRole("heading", { name: "Communications" }).waitFor()
		const editor = page.locator(".composer .ProseMirror")
		await editor.click()
		await editor.fill(text)
		await page.getByRole("button", { name: "Send" }).click()

		await expect(page.getByText(/Queued for \d+ guests?/)).toBeVisible()
		await expect(page.getByRole("button", { name: `Open message ${text}` })).toBeVisible()
	})

	test("sets the team's reply-to address", async ({ page }) => {
		const email = `reply-${Date.now()}@example.com`
		await page.getByRole("button", { name: "Email settings" }).click()
		const dialog = page.getByRole("dialog")
		await dialog.getByLabel("Support email").fill(email)
		await dialog.getByRole("button", { name: "Save" }).click()

		await expect(page.getByText("Reply-to address saved")).toBeVisible()
		await page.reload()
		await expect(page.getByText(email, { exact: true })).toBeVisible({ timeout: 15000 })
	})
})
