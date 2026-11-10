import { test, expect } from "@playwright/test"

import { BookingPage } from "../pages"

const uid = Date.now()

test.describe("Offline Payment Flow", () => {
	test("complete booking with offline payment", async ({ page }) => {
		const email = `offline-${uid}@test.com`
		const bookingPage = new BookingPage(page)

		await bookingPage.goto("offline-payment-e2e")
		await bookingPage.waitForFormLoad()

		await bookingPage.goToAttendees()
		await bookingPage.fillMyDetails("Test", "User", email)

		await bookingPage.payWith("Bank Transfer")

		// Wait for offline payment dialog
		await expect(page.getByRole("dialog").getByText("Bank Transfer")).toBeVisible({
			timeout: 10000,
		})
		await expect(page.getByText("Transfer to Account: 123456789")).toBeVisible()

		// Submit offline payment (no file upload required in test setup)
		const placed = page.waitForResponse((response) => response.url().includes("process_booking"))
		await page.getByRole("button", { name: "Submit" }).click()
		const bookingName = (await (await placed).json()).data.booking_name

		// The booker lands on the booking in the event drawer, awaiting verification.
		await expect(page).toHaveURL(/\/b\/manage\/events/, { timeout: 30000 })
		await expect(page.getByText("Payment Confirmation Pending")).toBeVisible({ timeout: 30000 })

		// A fresh booking link opens the same drawer.
		await page.goto(`/b/manage/events?booking=${bookingName}`)
		await expect(page.getByText("Payment Confirmation Pending")).toBeVisible({ timeout: 30000 })
	})

	test("offline payment dialog shows amount", async ({ page }) => {
		const bookingPage = new BookingPage(page)

		await bookingPage.goto("offline-payment-e2e")
		await bookingPage.waitForFormLoad()

		await bookingPage.goToAttendees()
		await bookingPage.fillMyDetails("Amount", "Test", `amount-${uid}@test.com`)

		await bookingPage.payWith("Bank Transfer")

		// Wait for dialog and verify amount is displayed in dialog
		const dialog = page.getByRole("dialog")
		await expect(dialog.getByText("₹500.00", { exact: true })).toBeVisible({ timeout: 10000 })
	})

	test("can cancel offline payment dialog", async ({ page }) => {
		const bookingPage = new BookingPage(page)

		await bookingPage.goto("offline-payment-e2e")
		await bookingPage.waitForFormLoad()

		await bookingPage.goToAttendees()
		await bookingPage.fillMyDetails("Cancel", "Test", `cancel-${uid}@test.com`)

		await bookingPage.payWith("Bank Transfer")

		await expect(page.getByRole("dialog").getByText("Bank Transfer")).toBeVisible({
			timeout: 10000,
		})

		// Click cancel
		await page.getByRole("button", { name: "Cancel" }).click()

		// Dialog should close
		await expect(page.getByRole("dialog").getByText("Bank Transfer")).not.toBeVisible({
			timeout: 5000,
		})
	})
})
