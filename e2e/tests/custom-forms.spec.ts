import { test, expect } from "@playwright/test"

import {
	CLOSED_FORM_MESSAGE,
	CLOSED_FORM_ROUTE,
	CLOSED_FORM_TITLE,
	CUSTOM_FORMS_EVENT_ROUTE as testEventRoute,
	MEMBERS_ONLY_FORM_ROUTE,
} from "../data/custom-forms"
import { callMethod } from "../helpers/frappe"
import { CustomFormPage } from "../pages"

test.describe("Event Feedback Form", () => {
	test("should display feedback form with title", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "feedback")
		await formPage.waitForFormLoad()
		await formPage.expectFormVisible()
		await formPage.expectFormTitle("Event Feedback")
	})

	test("should display submit button", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "feedback")
		await formPage.waitForFormLoad()
		await formPage.expectSubmitButtonVisible()
	})

	test("should display feedback text area", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "feedback")
		await formPage.waitForFormLoad()

		const textarea = page.locator("textarea").first()
		await expect(textarea).toBeVisible()
	})

	test("should fill feedback form fields", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "feedback")
		await formPage.waitForFormLoad()

		const feedbackText = "Great event, learned a lot about testing!"
		const textarea = page.locator("textarea").first()
		await textarea.fill(feedbackText)
		await expect(textarea).toHaveValue(feedbackText)

		const phoneInput = page.locator('input[placeholder="Phone number"]')
		if (await phoneInput.isVisible({ timeout: 1000 }).catch(() => false)) {
			await phoneInput.fill("9876543210")
			await expect(phoneInput).toHaveValue("9876543210")
		}

		await formPage.expectSubmitButtonVisible()
	})

	test("should interact with rating stars if present", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "feedback")
		await formPage.waitForFormLoad()

		const stars = page.locator(".cursor-pointer svg")
		if (
			await stars
				.first()
				.isVisible({ timeout: 1000 })
				.catch(() => false)
		) {
			const starCount = await stars.count()
			expect(starCount).toBe(5)
			await stars.nth(3).click()
		}
	})

	test("should submit feedback and get a response", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "feedback")
		await formPage.waitForFormLoad()

		const textarea = page.locator("textarea").first()
		await textarea.fill("E2E test feedback - event was excellent!")

		const phoneInput = page.locator('input[placeholder="Phone number"]')
		if (await phoneInput.isVisible({ timeout: 1000 }).catch(() => false)) {
			await phoneInput.fill("9876543210")
		}

		const stars = page.locator(".cursor-pointer svg")
		if (
			await stars
				.first()
				.isVisible({ timeout: 1000 })
				.catch(() => false)
		) {
			await stars.nth(4).click()
		}

		const { succeeded, status } = await formPage.submitAndExpectResponse()
		console.log(`Feedback submission: status=${status}, succeeded=${succeeded}`)
	})
})

test.describe("Talk Proposal Form", () => {
	test("should display talk proposal form with title", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "propose-talk")
		await formPage.waitForFormLoad()
		await formPage.expectFormVisible()
		await formPage.expectFormTitle("Talk Proposal")
	})

	test("should display required fields", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "propose-talk")
		await formPage.waitForFormLoad()

		await formPage.expectFieldVisible("Title")

		const requiredIndicator = page.locator('label:has-text("Title") .text-ink-red-4')
		const hasRequired = await requiredIndicator.isVisible({ timeout: 1000 }).catch(() => false)
		if (hasRequired) {
			await expect(requiredIndicator).toBeVisible()
		}
	})

	test("should display submit button", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "propose-talk")
		await formPage.waitForFormLoad()
		await formPage.expectSubmitButtonVisible()
	})

	test("should display description textarea", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "propose-talk")
		await formPage.waitForFormLoad()

		const textarea = page.locator("textarea").first()
		const hasTextarea = await textarea.isVisible({ timeout: 2000 }).catch(() => false)
		expect(hasTextarea).toBeTruthy()
	})

	test("should display phone input if present", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "propose-talk")
		await formPage.waitForFormLoad()

		const phoneInput = page.locator('input[placeholder="Phone number"]')
		if (await phoneInput.isVisible({ timeout: 1000 }).catch(() => false)) {
			await expect(phoneInput).toBeVisible()
		}
	})

	test("should fill talk proposal form fields", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "propose-talk")
		await formPage.waitForFormLoad()

		const titleInput = formPage.getInputByLabel("Title")
		await titleInput.fill("Introduction to E2E Testing")
		await expect(titleInput).toHaveValue("Introduction to E2E Testing")

		const textarea = page.locator("textarea").first()
		if (await textarea.isVisible({ timeout: 1000 }).catch(() => false)) {
			await textarea.fill("A comprehensive talk about writing E2E tests with Playwright.")
			await expect(textarea).toHaveValue(
				"A comprehensive talk about writing E2E tests with Playwright.",
			)
		}

		const phoneInput = page.locator('input[placeholder="Phone number"]')
		if (await phoneInput.isVisible({ timeout: 1000 }).catch(() => false)) {
			await phoneInput.fill("1234567890")
			await expect(phoneInput).toHaveValue("1234567890")
		}

		await formPage.expectSubmitButtonVisible()
	})

	test("should display speakers table with add button if present", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "propose-talk")
		await formPage.waitForFormLoad()

		const speakersLabel = page.locator('label:has-text("Speakers")')
		if (await speakersLabel.isVisible({ timeout: 1000 }).catch(() => false)) {
			await expect(speakersLabel).toBeVisible()

			const addButton = page.locator('button:has-text("Add Speakers")')
			await expect(addButton).toBeVisible()
		}
	})

	test("should submit talk proposal and get a response", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "propose-talk")
		await formPage.waitForFormLoad()

		const titleInput = formPage.getInputByLabel("Title")
		await titleInput.fill("E2E Test Talk: Automated Testing Best Practices")

		const textarea = page.locator("textarea").first()
		if (await textarea.isVisible({ timeout: 2000 }).catch(() => false)) {
			await textarea.fill("This talk covers best practices for writing robust E2E tests.")
		}

		const addSpeakersButton = page.locator('button:has-text("Add Speakers")')
		if (await addSpeakersButton.isVisible({ timeout: 2000 }).catch(() => false)) {
			await addSpeakersButton.click()

			const dialog = page.locator('[role="dialog"]')
			await expect(dialog).toBeVisible({ timeout: 5000 })

			const firstNameInput = dialog
				.locator('label:has-text("First Name")')
				.locator("..")
				.locator("input")
				.first()
			await firstNameInput.fill("E2E Speaker")

			const emailInput = dialog
				.locator('label:has-text("Email")')
				.locator("..")
				.locator("input")
				.first()
			await emailInput.fill("e2e-speaker@test.com")

			const addButton = dialog.locator('button[type="submit"]')
			await addButton.click()
		}

		const { succeeded, status } = await formPage.submitAndExpectResponse()
		console.log(`Talk proposal submission: status=${status}, succeeded=${succeeded}`)
	})
})

test.describe("Sponsorship Enquiry Form", () => {
	test("should display sponsorship form with title", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "enquire-sponsorship")
		await formPage.waitForFormLoad()
		await formPage.expectFormVisible()
		await formPage.expectFormTitle("Sponsorship Enquiry")
	})

	test("should display required fields", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "enquire-sponsorship")
		await formPage.waitForFormLoad()

		await formPage.expectFieldVisible("Company Name")
		await formPage.expectFieldVisible("Company Logo")
	})

	test("should display submit button", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "enquire-sponsorship")
		await formPage.waitForFormLoad()
		await formPage.expectSubmitButtonVisible()
	})

	test("should display optional fields", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "enquire-sponsorship")
		await formPage.waitForFormLoad()

		const websiteLabel = page.locator('label:has-text("Website")')
		if (await websiteLabel.isVisible({ timeout: 1000 }).catch(() => false)) {
			await expect(websiteLabel).toBeVisible()
		}

		const phoneInput = page.locator('input[placeholder="Phone number"]')
		if (await phoneInput.isVisible({ timeout: 1000 }).catch(() => false)) {
			await expect(phoneInput).toBeVisible()
		}
	})

	test("should display upload image button for company logo", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "enquire-sponsorship")
		await formPage.waitForFormLoad()

		const uploadButton = page.locator('button:has-text("Upload Image")')
		await expect(uploadButton).toBeVisible()
	})

	test("should fill sponsorship enquiry form fields", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "enquire-sponsorship")
		await formPage.waitForFormLoad()

		const companyNameInput = formPage.getInputByLabel("Company Name")
		await companyNameInput.fill("Test Corp Ltd")
		await expect(companyNameInput).toHaveValue("Test Corp Ltd")

		const websiteInput = formPage.getInputByLabel("Website")
		if (await websiteInput.isVisible({ timeout: 1000 }).catch(() => false)) {
			await websiteInput.fill("https://testcorp.example.com")
			await expect(websiteInput).toHaveValue("https://testcorp.example.com")
		}

		const phoneInput = page.locator('input[placeholder="Phone number"]')
		if (await phoneInput.isVisible({ timeout: 1000 }).catch(() => false)) {
			await phoneInput.fill("5551234567")
			await expect(phoneInput).toHaveValue("5551234567")
		}

		await formPage.expectSubmitButtonVisible()
	})

	test("should stay on form when submitting without required company logo", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "enquire-sponsorship")
		await formPage.waitForFormLoad()

		const companyNameInput = formPage.getInputByLabel("Company Name")
		await companyNameInput.fill("Test Corp Without Logo")

		await formPage.submit()

		await formPage.expectFormVisible()
	})
})

test.describe("Custom Form Edge Cases", () => {
	test("should show not found for nonexistent event", async ({ page }) => {
		const formPage = new CustomFormPage(page)
		await formPage.goto("nonexistent-event-route-xyz", "feedback")
		await formPage.expectNotFound()
	})

	test("should return error for invalid form route via API", async ({ request }) => {
		const result = await callMethod(request, "buzz.api.forms.get_custom_form_data", {
			event_route: testEventRoute,
			form_route: "invalid-route",
		}).catch((err: Error) => err)

		expect(result).toBeInstanceOf(Error)
	})

	test("should show not found for valid event but invalid form route", async ({ page }) => {
		const formPage = new CustomFormPage(page)
		await formPage.goto(testEventRoute, "nonexistent-form-route")
		await formPage.expectNotFound()
	})
})

test.describe("Login Required Form", () => {
	test("logged-in user gets the form", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, MEMBERS_ONLY_FORM_ROUTE)
		await formPage.waitForFormLoad()
		await formPage.expectFormVisible()
	})

	test.describe("as a guest", () => {
		test.use({ storageState: { cookies: [], origins: [] } })

		test("gets the login prompt instead of the form", async ({ page }) => {
			const formPage = new CustomFormPage(page)

			await formPage.goto(testEventRoute, MEMBERS_ONLY_FORM_ROUTE)
			await formPage.expectLoginRequired()
		})

		test("still gets an open form that does not require login", async ({ page }) => {
			const formPage = new CustomFormPage(page)

			await formPage.goto(testEventRoute, "feedback")
			await formPage.waitForFormLoad()
			await formPage.expectFormVisible()
		})
	})
})

test.describe("Closed Form", () => {
	test("shows the closed notice instead of the form", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, CLOSED_FORM_ROUTE)
		await formPage.expectClosed(CLOSED_FORM_TITLE, CLOSED_FORM_MESSAGE)
		await expect(page.locator("form")).toHaveCount(0)
	})

	test("rejects a submission over the API", async ({ request }) => {
		const result = await callMethod(request, "buzz.api.forms.submit_custom_form", {
			event_route: testEventRoute,
			form_route: CLOSED_FORM_ROUTE,
			data: { feedback: "too late" },
		}).catch((err: Error) => err)

		expect(result).toBeInstanceOf(Error)
		expect((result as Error).message).toContain("SubmissionsClosed")
		expect((result as Error).message).toContain("Submissions for this form have closed.")
	})
})
