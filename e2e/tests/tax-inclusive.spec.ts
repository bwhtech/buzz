import { test, expect } from "@playwright/test"

import { updateDoc, getList } from "../helpers/frappe"
import { BookingPage } from "../pages"

interface NamedDoc {
	name: string
}

test.describe("Tax Inclusive Pricing", () => {
	const testEventRoute = "test-event-e2e"

	test("should show tax as inclusive with correct amounts", async ({ page, request }) => {
		// Find the test event
		const events = await getList<NamedDoc>(request, "Buzz Event", {
			filters: { route: ["=", testEventRoute] },
		})
		expect(events.length).toBeGreaterThan(0)
		const eventName = events[0].name

		// Enable tax-inclusive pricing on the event
		await updateDoc(request, "Buzz Event", eventName, {
			apply_tax: 1,
			tax_inclusive: 1,
			tax_label: "GST",
			tax_percentage: 18,
		})

		const bookingPage = new BookingPage(page)
		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()

		// Fill attendee details to trigger summary
		await bookingPage.fillAttendeeDetails("Tax Test User", "taxtest@example.com")

		// Wait for the booking summary to render
		const summarySection = page.locator("text=Booking Summary")
		await expect(summarySection).toBeVisible({ timeout: 10000 })

		// Subtotal should be hidden for tax-inclusive (no discount case)
		const subtotalLabel = page.locator("span:text-is('Subtotal')")
		await expect(subtotalLabel).not.toBeVisible()

		// Tax should NOT appear as a separate line item
		// The "Inclusive of" note contains GST 18%, but there should be no standalone tax row
		const separateTaxRow = page.locator(".flex.justify-between:has(span:text-is('GST (18%)'))")
		await expect(separateTaxRow).not.toBeVisible()

		// Verify the "Inclusive of" note appears below the total
		const inclusiveNote = page.locator("text=/Inclusive of/")
		await expect(inclusiveNote).toBeVisible({ timeout: 5000 })

		// Verify the note contains GST and 18%
		const noteText = await inclusiveNote.textContent()
		expect(noteText).toContain("GST")
		expect(noteText).toContain("18%")

		// Verify the total shows the ticket price (unchanged by tax)
		const totalHeading = page.locator("h3:has-text('Total')")
		const totalContainer = totalHeading.locator("..")
		const totalText = await totalContainer.textContent()
		const totalMatch = totalText?.match(/[\d,]+/)
		expect(totalMatch).toBeTruthy()
		expect(totalMatch![0]).toBe("500")

		console.log(`Tax inclusive test passed: Total=500, note="${noteText?.trim()}"`)
	})

	test("should show tax as exclusive with increased total", async ({ page, request }) => {
		// Find the test event
		const events = await getList<NamedDoc>(request, "Buzz Event", {
			filters: { route: ["=", testEventRoute] },
		})
		expect(events.length).toBeGreaterThan(0)
		const eventName = events[0].name

		// Enable tax-exclusive pricing on the event
		await updateDoc(request, "Buzz Event", eventName, {
			apply_tax: 1,
			tax_inclusive: 0,
			tax_label: "GST",
			tax_percentage: 18,
		})

		const bookingPage = new BookingPage(page)
		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()

		// Fill attendee details to trigger summary
		await bookingPage.fillAttendeeDetails("Tax Test User", "taxtest@example.com")

		// Wait for the booking summary to render
		const summarySection = page.locator("text=Booking Summary")
		await expect(summarySection).toBeVisible({ timeout: 10000 })

		// Verify tax label does NOT show "Incl."
		const taxLineInclusive = page.locator("text=/GST.*18.*%.*Incl/")
		await expect(taxLineInclusive).not.toBeVisible()

		// Verify tax line exists without "Incl."
		const taxLine = page.locator("text=/GST.*18.*%/")
		await expect(taxLine).toBeVisible({ timeout: 5000 })

		// For exclusive tax: total should be greater than subtotal
		const totalHeading = page.locator("h3:has-text('Total')")
		const totalContainer = totalHeading.locator("..")
		const totalText = await totalContainer.textContent()

		const subtotalContainer = page.locator("span:text-is('Subtotal')").locator("..")
		const subtotalText = await subtotalContainer.textContent()

		const subtotalMatch = subtotalText?.match(/[\d,]+/)
		const totalMatch = totalText?.match(/[\d,]+/)

		expect(subtotalMatch).toBeTruthy()
		expect(totalMatch).toBeTruthy()

		const subtotalNum = parseInt(subtotalMatch![0].replace(/,/g, ""))
		const totalNum = parseInt(totalMatch![0].replace(/,/g, ""))

		// Total should be greater than subtotal for exclusive tax
		expect(totalNum).toBeGreaterThan(subtotalNum)

		console.log(`Tax exclusive test passed: Subtotal=${subtotalNum}, Total=${totalNum}`)
	})

	// Clean up: disable tax after tests
	test.afterAll(async ({ request }) => {
		const events = await getList<NamedDoc>(request, "Buzz Event", {
			filters: { route: ["=", testEventRoute] },
		})
		if (events.length > 0) {
			await updateDoc(request, "Buzz Event", events[0].name, {
				apply_tax: 0,
				tax_inclusive: 0,
			})
		}
	})
})
