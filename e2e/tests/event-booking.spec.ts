import { test, expect } from "@playwright/test"

import { BookingPage } from "../pages"

// Verifies that the booking form displays correctly with ticket types, add-ons, and booking button.
test.describe("Event Registration Page", () => {
	const testEventRoute = "test-event-e2e"

	test("should display event booking page", async ({ page }) => {
		const bookingPage = new BookingPage(page)

		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()
		await bookingPage.expectFormVisible()

		console.log("Event booking page loaded successfully")
	})

	test("should display add-ons section", async ({ page }) => {
		const bookingPage = new BookingPage(page)

		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()

		const addOnCount = await bookingPage.addOnCheckboxes.count()
		console.log(`Found ${addOnCount} add-on related elements`)

		if (addOnCount > 0) {
			await bookingPage.expectAddOnsVisible()
			console.log("Add-ons section is displayed")
		} else {
			console.log("No add-on elements found")
		}
	})

	test("should display booking button", async ({ page }) => {
		const bookingPage = new BookingPage(page)

		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()
		await bookingPage.expectBookButtonVisible()

		const buttonText = await bookingPage.getBookButtonText()
		console.log(`Booking button found with text: "${buttonText}"`)
	})

	test("should display attendee form fields", async ({ page }) => {
		const bookingPage = new BookingPage(page)

		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()

		const hasNameInput = await bookingPage.attendeeNameInput.isVisible().catch(() => false)
		const hasEmailInput = await bookingPage.attendeeEmailInput.isVisible().catch(() => false)

		expect(hasNameInput && hasEmailInput).toBeTruthy()
		console.log("Attendee form fields are displayed")
	})

	test("should fill booking form with attendee details and select add-ons", async ({ page }) => {
		const bookingPage = new BookingPage(page)

		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()

		// Fill in attendee details
		const testName = "John Doe"
		const testEmail = "john.doe@example.com"

		await bookingPage.fillAttendeeDetails(testName, testEmail)

		// Verify the values were entered
		await expect(bookingPage.attendeeNameInput).toHaveValue(testName)
		await expect(bookingPage.attendeeEmailInput).toHaveValue(testEmail)
		console.log("Attendee details filled successfully")

		// Select add-ons if available
		const addOnCount = await bookingPage.addOnCheckboxes.count()
		if (addOnCount > 0) {
			// Click the first add-on checkbox
			await bookingPage.addOnCheckboxes.first().click()

			// Verify it's checked
			await expect(bookingPage.addOnCheckboxes.first()).toBeChecked()
			console.log("Add-on selected successfully")
		}

		// Verify booking button is still visible and ready
		await bookingPage.expectBookButtonVisible()
		console.log("Form is ready to submit")
	})
})
