import { expect, test } from "@playwright/test"

import { ATTENDEE_EMAIL, ATTENDEE_PASSWORD } from "../data/tickets"

// Runs under the shared Administrator state, who owns a team. The non-member case logs the
// attendee in over it — that user is seeded by tickets.setup.ts and joins no team.
test.describe("Manage access", () => {
	test("sends a team member to the manage dashboard", async ({ page }) => {
		await page.goto("/b/")

		await expect(page).toHaveURL(/\/b\/manage\/events$/, { timeout: 15000 })
		await expect(page.getByRole("heading", { name: "Events", level: 1 })).toBeVisible()
	})

	test("routes a sidebar item with no page yet to the placeholder", async ({ page }) => {
		await page.goto("/b/manage/events")
		await page.getByRole("link", { name: "Sponsorship" }).click()

		await expect(page).toHaveURL(/\/b\/manage\/sponsorship$/)
		await expect(page.getByText("Work in progress")).toBeVisible()
	})

	test("shows a 404 for a manage section that does not exist", async ({ page }) => {
		await page.goto("/b/manage/evnets")

		await expect(page.getByText("Page not found")).toBeVisible({ timeout: 15000 })
	})

	test.describe("without a team", () => {
		test.beforeEach(async ({ page }) => {
			const response = await page.request.post("/api/method/login", {
				form: { usr: ATTENDEE_EMAIL, pwd: ATTENDEE_PASSWORD },
			})
			expect(response.ok()).toBeTruthy()
		})

		test("lands on the attendee dashboard", async ({ page }) => {
			await page.goto("/b/")

			await expect(page).toHaveURL(/\/b\/account\/bookings$/, { timeout: 15000 })
		})

		test("gets a 404 in place at /manage", async ({ page }) => {
			await page.goto("/b/manage")

			// /manage redirects to the landing page before the layout decides anyone is
			// unwelcome, so the 404 renders at /manage/events, not at /manage.
			await expect(page.getByText("Page not found")).toBeVisible({ timeout: 15000 })
			await expect(page).toHaveURL(/\/b\/manage\/events$/)
		})
	})

	test("shows a 404 for an unknown path", async ({ page }) => {
		await page.goto("/b/no-such-page")

		await expect(page.getByText("Page not found")).toBeVisible({ timeout: 15000 })
	})
})
