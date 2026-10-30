import { expect, test } from "@playwright/test"

test.describe("Event cards", () => {
	test("switches between the timeline and cards, and keeps the choice", async ({ page }) => {
		await page.goto("/b/manage/events")
		const firstCard = page.locator(".buzz-event-card").first()
		await expect(firstCard).toHaveAttribute("data-layout", "row", { timeout: 15000 })

		await page.getByRole("radio", { name: "Cards" }).click()
		await expect(firstCard).toHaveAttribute("data-layout", "cover")

		await page.reload()
		await expect(page.locator(".buzz-event-card").first()).toHaveAttribute("data-layout", "cover", {
			timeout: 15000,
		})

		await page.getByRole("radio", { name: "Timeline" }).click()
		await expect(page.locator(".buzz-event-card").first()).toHaveAttribute("data-layout", "row")
	})

	test("opens the event drawer from anywhere on the card", async ({ page }) => {
		await page.goto("/b/manage/events")
		await page.locator(".buzz-event-card-target").first().click({ timeout: 15000 })
		await expect(page.getByRole("dialog")).toBeVisible()
	})
})
