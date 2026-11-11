import { expect, test } from "@playwright/test"

import { ATTENDEE_EMAIL, ATTENDEE_PASSWORD } from "../data/tickets"
import { SETTINGS_STATE_PATH } from "../data/user-settings"

// Runs under the shared Administrator state, who owns a team. The non-member case logs the
// attendee in over it — that user is seeded by tickets.setup.ts and joins no team.
test.describe("Manage access", () => {
	test("sends a team member to the manage dashboard", async ({ page }) => {
		await page.goto("/b/")

		await expect(page).toHaveURL(/\/b\/manage\/events$/, { timeout: 15000 })
		await expect(page.getByRole("heading", { name: "Events", level: 1 })).toBeVisible()
	})

	test.describe("for a member who never enquired", () => {
		// The shared user files a sponsorship inquiry in custom-forms.spec.ts, which may run alongside.
		test.use({ storageState: SETTINGS_STATE_PATH })

		test("keeps Sponsorship out of the sidebar until there is an inquiry", async ({ page }) => {
			await page.goto("/b/manage/events")

			// The heading first: the sidebar is only worth counting once the shell has rendered.
			await expect(page.getByRole("heading", { name: "Events", level: 1 })).toBeVisible()
			await expect(page.getByRole("link", { name: "Sponsorship" })).toHaveCount(0)
		})
	})

	test("routes a section with no page yet to the placeholder", async ({ page }) => {
		await page.goto("/b/manage/overview")

		await expect(page.getByText("Work in progress")).toBeVisible({ timeout: 15000 })
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

		test("lands on the events feed", async ({ page }) => {
			await page.goto("/b/")

			await expect(page).toHaveURL(/\/b\/manage\/events$/, { timeout: 15000 })
			await expect(page.getByRole("heading", { name: "Events", level: 1 })).toBeVisible()
		})

		test("keeps the old bookings and tickets paths on the events feed", async ({ page }) => {
			for (const path of ["/b/bookings", "/b/tickets"]) {
				await page.goto(path)
				await expect(page).toHaveURL(/\/b\/manage\/events$/, { timeout: 15000 })
			}
		})
	})

	test("shows a 404 for an unknown path", async ({ page }) => {
		await page.goto("/b/no-such-page")

		await expect(page.getByText("Page not found")).toBeVisible({ timeout: 15000 })
	})
})
