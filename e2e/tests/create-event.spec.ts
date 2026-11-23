import { expect, test } from "@playwright/test"

test.describe("Create event", () => {
	test("offers a title and a way to save", async ({ page }) => {
		await page.goto("/b/manage/events")
		await page.getByRole("link", { name: "Events", exact: true }).click()
		await page.getByRole("link", { name: "Create Event" }).click()

		await expect(page).toHaveURL(/\/b\/manage\/team\/events\/new$/, { timeout: 15000 })
		await expect(page.getByRole("textbox", { name: "Event title" })).toBeVisible()
		// Nothing is filled in yet, so the button stays live and says what is missing
		// rather than leaving the organiser guessing what would enable it.
		const create = page.getByRole("button", { name: "Create", exact: true })
		await expect(create).toBeEnabled()
		await create.click()
		// The date and the venue can be announced later, so only the name is outstanding.
		const missing = page.getByRole("status").filter({ hasText: "Add these to create the event" })
		await expect(missing).toContainText("Name")
		await expect(missing).not.toContainText("Venue")
	})
})
