import { expect, test } from "@playwright/test"

import { TICKETS_EVENT_TITLE } from "../data/tickets"
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

		test("open the proposals timeline", async ({ page }) => {
			await page.goto("/b/account/proposals")

			await expect(page).toHaveURL(/\/b\/manage\/proposals$/, { timeout: 15000 })
		})

		test("open the linked proposal in its drawer", async ({ page }) => {
			await page.goto(`/b/account/proposals/${proposal}`)

			await expect(page.getByRole("dialog").getByText(PROPOSAL_TITLE).first()).toBeVisible({
				timeout: 15000,
			})
			await expect(page).toHaveURL(/\/b\/manage\/proposals(\?tab=\w+)?$/)
		})
	})
})
