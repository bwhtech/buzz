import { expect, test } from "@playwright/test"

// The three levels that produce a title: the router's afterEach for static routes,
// ManagerLayout for event-scoped ones, and a page's own usePageMeta for titles that
// need loaded data.
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

		// Whichever event the first card opens — the title comes from the event, not
		// from the route.
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

		// The stale-title case the afterEach exists for: usePageMeta never restores.
		await page.goto("/b/account/tickets")
		await expect(page).toHaveTitle("My Tickets | Buzz")
	})
})
