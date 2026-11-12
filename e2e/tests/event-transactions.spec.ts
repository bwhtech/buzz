import { expect, test, type Page } from "@playwright/test"

import { getList } from "../helpers/frappe"

// Runs under the shared Administrator state, on the event event.setup.ts seeds.
const TEST_EVENT_ROUTE = "test-event-e2e"

async function testEventName(page: Page) {
	const [event] = await getList<{ name: string }>(page.request, "Buzz Event", {
		filters: { route: ["=", TEST_EVENT_ROUTE] },
	})
	return event.name
}

test.describe("Event transactions", () => {
	test("the sidebar offers Transactions after Payments", async ({ page }) => {
		const event = await testEventName(page)
		await page.goto(`/b/manage/events/${event}/details`)

		const transactions = page.getByRole("link", { name: "Transactions" })
		await expect(transactions).toBeVisible({ timeout: 15000 })
		await transactions.click()

		await expect(page).toHaveURL(new RegExp(`/manage/events/${event}/transactions`))
		await expect(page.getByRole("banner").first()).toContainText("Transactions")
		await expect(
			page.getByRole("textbox", { name: /Search by booking, transaction ID/ }),
		).toBeVisible()
	})

	test("lists transactions or says there are none yet", async ({ page }) => {
		const event = await testEventName(page)
		await page.goto(`/b/manage/events/${event}/transactions`)

		await expect(page.getByRole("table").or(page.getByText("No transactions yet"))).toBeVisible({
			timeout: 15000,
		})
	})

	test("a ?booking= link opens that transaction in the drawer", async ({ page }) => {
		const event = await testEventName(page)
		const [booking] = await getList<{ name: string }>(page.request, "Event Booking", {
			filters: { event, docstatus: 1, total_amount: [">", 0] },
			limit: 1,
		})
		test.skip(!booking, "The seeded event has no paid booking")

		await page.goto(`/b/manage/events/${event}/transactions?booking=${booking.name}`)

		const drawer = page.getByRole("dialog")
		await expect(drawer).toBeVisible({ timeout: 15000 })
		await expect(drawer).toContainText(booking.name)
		await expect(drawer.getByRole("heading", { name: "Payment" })).toBeVisible()
		await expect(drawer.getByRole("heading", { name: "Amounts" })).toBeVisible()
	})
})
