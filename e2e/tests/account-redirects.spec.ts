import { expect, test } from "@playwright/test"

import { ATTENDEE_EMAIL, ATTENDEE_STATE_PATH, TICKETS_EVENT_TITLE } from "../data/tickets"
import { newApiContext } from "../helpers/auth"
import { createDoc, deleteDoc, getList } from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const PROPOSAL_TITLE = "E2E Redirected Proposal"

// /b/account was folded into /b/manage. Old links land on the page that replaced each
// tab, and an id in the old path opens its drawer there.
test.describe("Old account links", () => {
	test.describe("to talk proposals", () => {
		let proposal: string

		test.beforeAll(async ({ request }) => {
			const events = await getList<NamedDoc>(request, "Buzz Event", {
				filters: { title: ["=", TICKETS_EVENT_TITLE] },
			})
			const created = await createDoc<NamedDoc>(request, "Talk Proposal", {
				title: PROPOSAL_TITLE,
				event: events[0].name,
				speakers: [{ first_name: "Admin", email: "admin@example.com" }],
			})
			proposal = created.name
		})

		test.afterAll(async ({ request }) => {
			await deleteDoc(request, "Talk Proposal", proposal)
		})

		test("open the linked proposal in its drawer", async ({ page }) => {
			await page.goto(`/b/account/proposals/${proposal}`)

			await expect(page.getByRole("dialog").getByText(PROPOSAL_TITLE).first()).toBeVisible({
				timeout: 15000,
			})
			await expect(page).toHaveURL(/\/b\/manage\/proposals(\?tab=\w+)?$/)
		})
	})
	test.describe("to tickets", () => {
		test.use({ storageState: ATTENDEE_STATE_PATH })

		test("open the linked ticket's event drawer", async ({ page, baseURL }) => {
			const admin = await newApiContext(baseURL!)
			const [event] = await getList<NamedDoc>(admin, "Buzz Event", {
				filters: { title: ["=", TICKETS_EVENT_TITLE] },
			})
			const [ticket] = await getList<NamedDoc>(admin, "Event Ticket", {
				filters: { event: ["=", event.name], attendee_email: ["=", ATTENDEE_EMAIL] },
			})
			await admin.dispose()

			await page.goto(`/b/account/tickets/${ticket.name}`)

			await expect(page).toHaveURL(/\/b\/manage\/events/, { timeout: 15000 })
			const drawer = page.getByRole("dialog").filter({ hasText: TICKETS_EVENT_TITLE })
			await expect(drawer.getByText("You're in")).toBeVisible({ timeout: 15000 })
		})
	})
})
