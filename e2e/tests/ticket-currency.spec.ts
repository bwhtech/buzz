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

	test("falls back to INR until every item has a USD price", async ({ page }) => {
		await page.goto(`/b/register/${route}`)
		await expect(page.getByText("Showing INR prices")).toBeVisible({ timeout: 15000 })

		await page.getByRole("button", { name: "Change currency" }).click()
		await page.getByRole("menuitem", { name: /USD/ }).click()
		await expect(page.getByText("Showing USD prices")).toBeVisible()

		const ticketType = page.getByRole("combobox", { name: "Ticket Type" })
		await expect(ticketType).toContainText("INR only")
		const fallback = page.getByText("This order will be charged in INR")
		await expect(fallback).toBeVisible()

		await ticketType.click()
		await page.getByRole("option", { name: /^Standard .*\$15/ }).click()
		await expect(fallback).toBeHidden()
		await expect(page.getByText("Pay by card. You're charged in USD.")).toBeVisible()
	})
})
