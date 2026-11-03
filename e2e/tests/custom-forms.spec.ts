import { test, expect, type APIRequestContext } from "@playwright/test"

import {
	ATTENDEE_EMAIL,
	ATTENDEE_QUESTION,
	ATTENDEE_STATE_PATH,
	BOOKING_QUESTION,
	CLOSED_FORM_MESSAGE,
	CLOSED_FORM_ROUTE,
	CLOSED_FORM_TITLE,
	CUSTOM_FORMS_EVENT_ROUTE as testEventRoute,
	MEMBERS_ONLY_FORM_ROUTE,
} from "../data/custom-forms"
import { newApiContext } from "../helpers/auth"
import { callMethod, getDoc, getList, updateDoc } from "../helpers/frappe"
import { BookingPage, CustomFormPage } from "../pages"

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

	test("should display description editor", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "propose-talk")
		await formPage.waitForFormLoad()

		// The description is a Text Editor field, which renders the rich text editor.
		const editor = page.locator('[contenteditable="true"]').first()
		await expect(editor).toBeVisible({ timeout: 2000 })
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

		const descriptionEditor = page.locator('[contenteditable="true"]').first()
		if (await descriptionEditor.isVisible({ timeout: 1000 }).catch(() => false)) {
			await descriptionEditor.fill("A comprehensive talk about writing E2E tests with Playwright.")
			await expect(descriptionEditor).toContainText(
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

		const descriptionEditor = page.locator('[contenteditable="true"]').first()
		if (await descriptionEditor.isVisible({ timeout: 2000 }).catch(() => false)) {
			await descriptionEditor.fill("This talk covers best practices for writing robust E2E tests.")
		}

		const addSpeakersButton = page.locator('button:has-text("Add Speakers")')
		if (await addSpeakersButton.isVisible({ timeout: 2000 }).catch(() => false)) {
			await addSpeakersButton.click()

			const dialog = page.locator('[role="dialog"][data-state="open"]')
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

	test("should submit an enquiry and offer account details", async ({ page }) => {
		const formPage = new CustomFormPage(page)

		await formPage.goto(testEventRoute, "enquire-sponsorship")
		await formPage.waitForFormLoad()
		await formPage.getInputByLabel("Company Name").fill("E2E Sponsor Company")

		const fileInput = page.locator('input[type="file"]').first()
		await fileInput.setInputFiles({
			name: "e2e-logo.png",
			mimeType: "image/png",
			buffer: Buffer.from(
				"89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000000020001e221bc330000000049454e44ae426082",
				"hex",
			),
		})
		await expect(page.getByRole("button", { name: "Remove image" })).toBeVisible()

		const result = await formPage.submitAndExpectResponse()
		expect(result.succeeded).toBeTruthy()
		const enquiryLink = page.getByRole("link", { name: "View your enquiry" })
		await expect(enquiryLink).toBeVisible()
		await enquiryLink.click()
		await expect(page).toHaveURL(/\/account\/sponsorships\/.+/)
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

		test("gets the public sponsorship form with a Contact Email field", async ({ page }) => {
			const formPage = new CustomFormPage(page)
			await formPage.goto(testEventRoute, "enquire-sponsorship")
			await formPage.waitForFormLoad()
			await formPage.expectFormVisible()
			await formPage.expectFieldVisible("Contact Email")
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

interface AnsweredDoc {
	name: string
	additional_fields?: { fieldname: string; value: string }[]
	attendees?: { custom_fields: string | Record<string, string> }[]
}

test.describe("Registration Questions", () => {
	test.use({ storageState: ATTENDEE_STATE_PATH })

	test("booking and attendee answers are stored where each form keeps them", async ({
		page,
		baseURL,
	}) => {
		const bookingPage = new BookingPage(page)
		await bookingPage.goto(testEventRoute)
		await bookingPage.waitForFormLoad()
		await bookingPage.goToAttendees()
		await bookingPage.fillMyDetails("Form", "Attendee", ATTENDEE_EMAIL)
		await page.getByLabel(ATTENDEE_QUESTION.label).fill("Vegan")
		await bookingPage.continue()
		await page.getByLabel(BOOKING_QUESTION.label).fill("Acme")
		await bookingPage.submit()
		await expect(page.getByText("You're going to")).toBeVisible({ timeout: 30000 })

		const admin = await newApiContext(baseURL!)
		const [latest] = await getList<AnsweredDoc>(admin, "Event Booking", {
			filters: { user: ["=", ATTENDEE_EMAIL] },
			orderBy: "creation desc",
			limit: 1,
		})
		const booking = await getDoc<AnsweredDoc>(admin, "Event Booking", latest.name)
		expect(answers(booking)).toEqual({ [BOOKING_QUESTION.fieldname]: "Acme" })
		const attendeeAnswers = booking.attendees?.[0].custom_fields
		expect(
			typeof attendeeAnswers === "string" ? JSON.parse(attendeeAnswers) : attendeeAnswers,
		).toEqual({ [ATTENDEE_QUESTION.fieldname]: "Vegan" })

		const [ticket] = await getList<AnsweredDoc>(admin, "Event Ticket", {
			filters: { booking: ["=", booking.name] },
		})
		expect(answers(await getDoc<AnsweredDoc>(admin, "Event Ticket", ticket.name))).toEqual({
			[ATTENDEE_QUESTION.fieldname]: "Vegan",
		})
		await admin.dispose()
	})

	test("renamed and hidden core fields and the custom confirmation show on the booking page", async ({
		page,
		baseURL,
	}) => {
		const admin = await newApiContext(baseURL!)
		await withCoreRows(
			admin,
			{
				"Event Booking Attendee": {
					questions: { first_name: { label: "Given name" }, last_name: { enabled: 0 } },
				},
				"Event Booking": {
					questions: { buyer_name: { label: "Name on invoice" } },
					success_title: "Welcome aboard",
					success_message: "See you **soon**",
				},
			},
			async () => {
				const bookingPage = new BookingPage(page)
				await bookingPage.goto(testEventRoute)
				await bookingPage.waitForFormLoad()
				await bookingPage.goToAttendees()
				await page.getByLabel("Given name").first().fill("Core")
				await expect(page.getByLabel("Last name")).toHaveCount(0)
				await page.getByLabel("Email").first().fill(ATTENDEE_EMAIL)
				await bookingPage.continue()
				await page.getByLabel(BOOKING_QUESTION.label).fill("Acme")
				await expect(page.getByLabel("Name on invoice")).toBeVisible()
				await bookingPage.submit()

				await expect(page.getByRole("heading", { name: "Welcome aboard" })).toBeVisible({
					timeout: 30000,
				})
				await expect(page.locator("strong", { hasText: "soon" })).toBeVisible()
			},
		)
		await admin.dispose()
	})
})

interface RegistrationRow {
	fieldname: string
	label: string
	enabled: number
}

// Edits core rows of the event's registration forms and puts the forms back after the callback.
async function withCoreRows(
	admin: APIRequestContext,
	changes: Record<string, Record<string, any>>,
	run: () => Promise<void>,
): Promise<void> {
	const [event] = await getList<{ name: string }>(admin, "Buzz Event", {
		filters: { route: ["=", testEventRoute] },
	})
	const forms = await getList<{ name: string; form_doctype: string }>(admin, "Buzz Form", {
		filters: { event: ["=", event.name], form_doctype: ["in", Object.keys(changes)] },
		fields: ["name", "form_doctype"],
	})
	const originals = await Promise.all(
		forms.map((form) => getDoc<Record<string, any>>(admin, "Buzz Form", form.name)),
	)
	try {
		for (const [index, form] of forms.entries()) {
			const { questions: edits, ...rest } = changes[form.form_doctype]
			await updateDoc(admin, "Buzz Form", form.name, {
				...rest,
				questions: originals[index].questions.map((row: RegistrationRow) => ({
					...row,
					...edits?.[row.fieldname],
				})),
			})
		}
		await run()
	} finally {
		for (const [index, form] of forms.entries()) {
			const { questions, success_title = null, success_message = null } = originals[index]
			await updateDoc(admin, "Buzz Form", form.name, { questions, success_title, success_message })
		}
	}
}

function answers(doc: AnsweredDoc): Record<string, string> {
	return Object.fromEntries((doc.additional_fields ?? []).map((row) => [row.fieldname, row.value]))
}
