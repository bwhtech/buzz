import { test, expect, type Page } from "@playwright/test"

import { AUTOMATIC_OFFER_TITLE, COUPON_EVENT_ROUTE } from "../data/coupons"
import { BookingPage } from "../pages"

async function openBookingForm(page: Page) {
	const bookingPage = new BookingPage(page)
	await bookingPage.goto(COUPON_EVENT_ROUTE)
	await bookingPage.waitForFormLoad()
	await bookingPage.goToAttendees()
}

const summary = (page: Page) => page.locator("aside")
const automaticDiscount = (page: Page) =>
	summary(page).locator("dt", { hasText: `Discount · ${AUTOMATIC_OFFER_TITLE}` })

async function applyCode(page: Page, code: string) {
	await page.getByRole("button", { name: "Add discount code" }).click()
	await page.getByLabel("Discount code").fill(code)
	await page.getByRole("button", { name: "Apply", exact: true }).click()
}

test.describe("Coupons", () => {
	test("promo code replaces the automatic discount and removing it brings it back", async ({
		page,
	}) => {
		await openBookingForm(page)
		await expect(automaticDiscount(page)).toBeVisible()
		await expect(
			summary(page)
				.getByText(/₹100$/)
				.first(),
		).toBeVisible()

		await applyCode(page, "E2EPROMO")
		await expect(summary(page).locator("dt", { hasText: "Discount · E2EPROMO" })).toBeVisible()
		await expect(automaticDiscount(page)).toHaveCount(0)
		await expect(
			summary(page)
				.getByText(/₹50$/)
				.first(),
		).toBeVisible()

		await page.getByRole("button", { name: "Remove code" }).click()
		await expect(automaticDiscount(page)).toBeVisible()
		await expect(
			summary(page)
				.getByText(/₹100$/)
				.first(),
		).toBeVisible()
	})

	test("unknown code shows an error and keeps the automatic discount", async ({ page }) => {
		await openBookingForm(page)
		await applyCode(page, "NOSUCHCODE")
		await expect(page.getByText("Invalid or expired code")).toBeVisible()
		await expect(automaticDiscount(page)).toBeVisible()
	})
})
