import { expect, test } from "@playwright/test"

import {
	createDoc,
	deleteDoc,
	ensureEventHost,
	ensureTestTeam,
	openRegistrations,
} from "../helpers/frappe"

interface NamedDoc {
	name: string
}

// Seeds its own event: one ticket priced in INR and USD, one sold in INR only. The booking
// page lists the newest ticket type first, so the INR-only one is preselected.
test.describe("Ticket currencies", () => {
	const route = `currency-e2e-${Date.now()}`
	let eventId: string

	test.beforeAll(async ({ request }) => {
		const team = await ensureTestTeam(request)
		const event = await createDoc<NamedDoc>(request, "Buzz Event", {
			team,
			title: "E2E Currency Event",
			category: "E2E Test Category",
			host: await ensureEventHost(request, "E2E Test Host", team),
			start_date: "2030-01-01",
			route,
			is_published: 1,
			start_time: "09:00:00",
			end_time: "17:00:00",
			medium: "In Person",
		})
		eventId = event.name
		await openRegistrations(request, eventId)
		await createDoc(request, "Event Ticket Type", {
			event: eventId,
			title: "Standard",
			prices: [
				{ currency: "INR", price: 1000 },
				{ currency: "USD", price: 15 },
			],
		})
		await createDoc(request, "Event Ticket Type", {
			event: eventId,
			title: "Local",
			prices: [{ currency: "INR", price: 500 }],
		})
	})

	test.afterAll(async ({ request }) => {
		await deleteDoc(request, "Buzz Event", eventId).catch(() => {})
	})

	test("switching currency drops tickets it doesn't sell, with undo", async ({ page }) => {
		await page.goto(`/b/register/${route}`)
		const usd = page.getByRole("radio", { name: /USD/ })
		await expect(usd).toBeVisible({ timeout: 15000 })

		await usd.click()
		const removed = page.getByText("Removed Local. Not sold in USD.")
		await expect(removed).toBeVisible()
		await expect(page.getByText("Not sold in USD", { exact: true })).toBeVisible()

		await page.getByRole("button", { name: "Undo" }).click()
		await expect(page.getByRole("radio", { name: /INR/ })).toBeChecked()
		await expect(page.getByText("1 ticket selected")).toBeVisible()

		await usd.click()
		await page.getByRole("button", { name: "Add Standard" }).click()
		await expect(page.getByText("Pay in")).toBeVisible()
		await expect(page.locator("aside dd").last()).toHaveText("$15")
	})
})
