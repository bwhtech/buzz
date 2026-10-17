import { test, expect } from "@playwright/test"

import { BookingPage } from "../pages"

// Unique suffix per run to avoid rate limits
const uid = Date.now()

test.describe("Guest Booking UX", () => {
	test("guest details fill the first ticket and the buyer", async ({ page }) => {
		const bookingPage = new BookingPage(page)
		await bookingPage.goto("guest-no-otp-e2e")
		await bookingPage.waitForFormLoad()

		await bookingPage.goToAttendees()
		await bookingPage.fillMyDetails("Test", "Guest", "test@example.com")

		await expect(page.getByText("Issued to you")).toBeVisible()

		await bookingPage.continue()
		await expect(page.getByLabel("Email").first()).toHaveValue("test@example.com")
	})
})

test.describe("Guest Booking", () => {
	test("guest booking without OTP", async ({ page }) => {
		const email = `guest-no-otp-${uid}@test.com`
		const bookingPage = new BookingPage(page)
		await bookingPage.goto("guest-no-otp-e2e")
		await bookingPage.waitForFormLoad()

		await bookingPage.goToAttendees()
		await bookingPage.fillMyDetails("Test", "Guest", email)

		await bookingPage.submit()

		await expect(page.getByText("You're going to")).toBeVisible({ timeout: 30000 })
	})

	test("guest booking with Email OTP", async ({ page }) => {
		const email = `guest-email-otp-${uid}@test.com`
		const bookingPage = new BookingPage(page)
		await bookingPage.goto("guest-email-otp-e2e")
		await bookingPage.waitForFormLoad()

		await bookingPage.goToAttendees()
		await bookingPage.fillMyDetails("Test", "Guest Email", email)

		const otpResponsePromise = page.waitForResponse(
			(resp) => resp.url().includes("send_guest_booking_otp") && resp.status() === 200,
		)

		await bookingPage.submit()

		const otpResponse = await otpResponsePromise
		const otpData = (await otpResponse.json()) as { data?: { otp?: string } }
		const otp = otpData.data?.otp
		expect(otp).toBeTruthy()

		await expect(page.getByText("Verify your email")).toBeVisible({ timeout: 10000 })

		await page.locator('input[placeholder="123456"]').fill(otp!)
		await page.getByRole("button", { name: "Verify & Book" }).click()

		await expect(page.getByText("You're going to")).toBeVisible({ timeout: 30000 })
	})

	test("guest booking with Phone OTP", async ({ page }) => {
		const email = `guest-phone-otp-${uid}@test.com`
		const phone = `9${uid.toString().slice(-9)}`
		const bookingPage = new BookingPage(page)
		await bookingPage.goto("guest-phone-otp-e2e")
		await bookingPage.waitForFormLoad()

		await bookingPage.goToAttendees()
		await bookingPage.fillMyDetails("Test", "Guest Phone", email)
		await bookingPage.continue()
		await page.getByPlaceholder("Phone number").fill(phone)

		const otpResponsePromise = page.waitForResponse(
			(resp) => resp.url().includes("send_guest_booking_otp") && resp.status() === 200,
		)

		await bookingPage.submit()

		const otpResponse = await otpResponsePromise
		const otpData = (await otpResponse.json()) as { data?: { otp?: string } }
		const otp = otpData.data?.otp
		expect(otp).toBeTruthy()

		await expect(page.getByText("Verify your phone")).toBeVisible({ timeout: 10000 })

		await page.locator('input[placeholder="123456"]').fill(otp!)
		await page.getByRole("button", { name: "Verify & Book" }).click()

		await expect(page.getByText("You're going to")).toBeVisible({ timeout: 30000 })
	})

	test("guest phone field rejects a number of the wrong length", async ({ page }) => {
		const email = `guest-phone-invalid-${uid}@test.com`
		const bookingPage = new BookingPage(page)
		await bookingPage.goto("guest-phone-otp-e2e")
		await bookingPage.waitForFormLoad()

		await bookingPage.goToAttendees()
		await bookingPage.fillMyDetails("Test", "Guest Phone", email)

		// A well-formed but too-short number passes PhoneInput's digit filter and is
		// caught by the server, which reports it under the field rather than as a toast.
		await bookingPage.continue()
		const phoneInput = page.getByPlaceholder("Phone number")
		await phoneInput.fill("12345")
		await bookingPage.submit()

		await expect(page.getByText("is not valid")).toBeVisible({ timeout: 10000 })
		await expect(page.getByText("Verify your phone")).toBeHidden()
	})
})
