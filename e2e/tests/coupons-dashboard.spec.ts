import { test, expect, type Page } from "@playwright/test"

import { COUPON_EVENT_ROUTE } from "../data/coupons"
import { getList } from "../helpers/frappe"

async function openCouponsPage(page: Page) {
	const [event] = await getList<{ name: string }>(page.request, "Buzz Event", {
		filters: { route: ["=", COUPON_EVENT_ROUTE] },
	})
	await page.goto(`/b/manage/events/${event.name}/coupons`)
	await expect(page.getByRole("heading", { name: "Coupons" })).toBeVisible()
}

const couponCard = (page: Page, code: string) =>
	page.getByRole("button", { name: new RegExp(code) })

// Unique per run: the setup only clears coupons when it recreates the event.
const uniqueCode = () => `E2E${Date.now().toString(36).toUpperCase()}`

async function createPromoCode(page: Page, code: string) {
	await page.getByRole("button", { name: "Add" }).click()
	await expect(page.getByText("Step 1 of 2")).toBeVisible()
	await page.getByRole("button", { name: "Continue" }).click()
	await page.getByLabel("Code").fill(code)
	await page.getByRole("button", { name: "15%" }).click()
	await page.getByRole("button", { name: "Create coupon" }).click()
	await expect(page.getByText("Coupon created")).toBeVisible()
}

test.describe("Coupons dashboard", () => {
	test("creates a promo code through the stepped drawer", async ({ page }) => {
		const code = uniqueCode()
		await openCouponsPage(page)

		await createPromoCode(page, code)

		const card = couponCard(page, code)
		await expect(card).toContainText("15% off")
		await expect(card).toContainText("Active")
	})

	test("edits and disables a coupon", async ({ page }) => {
		const code = uniqueCode()
		await openCouponsPage(page)
		await createPromoCode(page, code)

		await couponCard(page, code).click()
		await page.getByRole("button", { name: "25%" }).click()
		await page.getByRole("button", { name: "Save changes" }).click()
		await expect(page.getByText("Coupon updated")).toBeVisible()
		await page.getByRole("button", { name: "Disable" }).click()
		await expect(page.getByText("Coupon is disabled")).toBeVisible()
		await page.keyboard.press("Escape")

		const card = couponCard(page, code)
		await expect(card).toContainText("25% off")
		await expect(card).toContainText("Disabled")
	})
})
