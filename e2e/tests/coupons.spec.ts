import { test, expect, type Page } from "@playwright/test"

import {
	ACCESS_CODE,
	AUTOMATIC_OFFER_TITLE,
	COUPON_EVENT_ROUTE,
	HIDDEN_TICKET_TITLE,
} from "../data/coupons"
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

test.describe("Access codes", () => {
	test("the hidden ticket stays off the form without a code", async ({ page }) => {
		const bookingPage = new BookingPage(page)
		await bookingPage.goto(COUPON_EVENT_ROUTE)
		await bookingPage.waitForFormLoad()
		await expect(page.getByText(HIDDEN_TICKET_TITLE)).toHaveCount(0)
	})

	test("an access link shows the hidden ticket and books it", async ({ page }) => {
		const bookingPage = new BookingPage(page)
		await bookingPage.goto(`${COUPON_EVENT_ROUTE}?code=${ACCESS_CODE}`)
		await bookingPage.waitForFormLoad()
		await expect(page.getByText(HIDDEN_TICKET_TITLE).first()).toBeVisible()

		const hiddenTicketAdd = page.getByRole("button", { name: `Add ${HIDDEN_TICKET_TITLE}` })
		if (await hiddenTicketAdd.count()) await hiddenTicketAdd.click()
		const standardRemove = page.getByRole("button", { name: "Remove one Standard Ticket" })
		if (await standardRemove.count()) await standardRemove.click()

		await bookingPage.goToAttendees()
		await bookingPage.fillAttendeeDetails("Insider Guest", "insider@example.com")
		await bookingPage.submit()
		await expect(page.getByText("You're going to")).toBeVisible({ timeout: 30000 })
	})

	test("a typed code unlocks the ticket and a wrong code shows an error", async ({ page }) => {
		const bookingPage = new BookingPage(page)
		await bookingPage.goto(COUPON_EVENT_ROUTE)
		await bookingPage.waitForFormLoad()

		await page.getByRole("button", { name: "Have an access code?" }).click()
		await page.getByLabel("Access code").fill("NOSUCHCODE")
		await page.getByLabel("Access code").press("Enter")
		await expect(page.getByText("Invalid or expired code").first()).toBeVisible()
		await expect(page.getByText(HIDDEN_TICKET_TITLE)).toHaveCount(0)

		await page.getByLabel("Access code").fill(ACCESS_CODE)
		await page.getByLabel("Access code").press("Enter")
		await expect(page.getByText(HIDDEN_TICKET_TITLE).first()).toBeVisible()
	})
})
