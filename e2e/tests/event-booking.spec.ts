import { test, expect } from "@playwright/test"

import { BookingPage } from "../pages"

// Walks the registration flow: tickets, then attendee details with their add-ons.
test.describe("Event Registration Page", () => {
	const testEventRoute = "test-event-e2e"

	test("shows tickets with a quantity picker first", async ({ page }) => {
		const bookingPage = new BookingPage(page)
		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()

		await expect(page.getByRole("heading", { name: "Choose tickets" })).toBeVisible()
		await expect(page.getByRole("button", { name: /^Remove one / }).first()).toBeVisible()
		await expect(page.getByRole("button", { name: "Continue to attendees" })).toBeVisible()
	})

	test("adding a ticket adds an attendee", async ({ page }) => {
		const bookingPage = new BookingPage(page)
		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()

		await page
			.getByRole("button", { name: /^Add one / })
			.first()
			.click()
		await expect(page.getByText("2 tickets selected")).toBeVisible()
		await bookingPage.goToAttendees()
		await expect(page.locator("article")).toHaveCount(2)
	})

	test("fills attendee details and selects add-ons", async ({ page }) => {
		const bookingPage = new BookingPage(page)
		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()
		await bookingPage.goToAttendees()

		await bookingPage.fillAttendeeDetails("John Doe", "john.doe@example.com")
		await expect(page.getByLabel("Email").first()).toHaveValue("john.doe@example.com")

		if (await bookingPage.addOnCheckboxes.count()) {
			await bookingPage.addOnCheckboxes.first().click()
			await expect(bookingPage.addOnCheckboxes.first()).toBeChecked()
		}
		await bookingPage.expectBookButtonVisible()
	})

	test("a missing attendee name blocks Continue", async ({ page }) => {
		const bookingPage = new BookingPage(page)
		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()
		await bookingPage.goToAttendees()

		await bookingPage.fillAttendeeDetails("", "")
		await bookingPage.continue()
		await expect(page.getByText("Enter a first name").first()).toBeVisible()
	})
})
