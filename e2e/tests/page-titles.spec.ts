import { expect, test } from "@playwright/test"

const EVENT_TITLE = "E2E Test Event"
const EVENT_ROUTE = "test-event-e2e"

test.describe("Page titles", () => {
	test("names the page and falls back to the app for context", async ({ page }) => {
		await page.goto("/b/manage/events")
		await expect(page).toHaveTitle("My Events | Buzz")

		await page.goto("/b/account/bookings")
		await expect(page).toHaveTitle("My Bookings | Buzz")
	})

	test("uses the event as context inside an event", async ({ page }) => {
		await page.goto("/b/manage/events")
		await page.getByRole("link", { name: "Manage" }).first().click()

		// Whichever event the first card opens: the title follows the event, not the route.
		const field = page.getByRole("textbox", { name: "Event title" })
		await expect(field).toBeVisible({ timeout: 15000 })
		const title = await field.inputValue()

		await expect(page).toHaveTitle(`Details | ${title}`)
		await page.getByRole("link", { name: "Guests" }).click()
		await expect(page).toHaveTitle(`Guests | ${title}`)
	})

	test("keeps a data-derived title, and drops it on the way out", async ({ page }) => {
		await page.goto(`/b/register/${EVENT_ROUTE}`)
		await expect(page).toHaveTitle(`Register | ${EVENT_TITLE}`, { timeout: 15000 })

		// usePageMeta never restores on unmount; the afterEach is what clears it.
		await page.goto("/b/account/tickets")
		await expect(page).toHaveTitle("My Tickets | Buzz")
	})
})
