import { expect, Locator, Page } from "@playwright/test"

// The registration flow: tickets, attendees, details, then a summary for paid orders.
const ADVANCES = /Continue to|Review booking/
export class BookingPage {
	private page: Page
	addOnCheckboxes: Locator
	continueButton: Locator
	private bookingForm: Locator

	constructor(page: Page) {
		this.page = page
		this.bookingForm = page.locator("form")
		this.continueButton = page.locator('button[type="submit"]')
		this.addOnCheckboxes = page
			.locator("article")
			.getByRole("checkbox", { name: /^(?!This is me)/ })
	}

	async goto(eventRoute: string): Promise<void> {
		await this.page.goto(`/b/register/${eventRoute}`)
		await this.page.waitForLoadState("networkidle")
	}

	async waitForFormLoad(): Promise<void> {
		await expect(this.bookingForm).toBeVisible({ timeout: 15000 })
	}

	async expectFormVisible(): Promise<void> {
		await expect(this.bookingForm).toBeVisible()
	}

	async continue(): Promise<void> {
		await this.continueButton.click()
	}

	// From the tickets step to the attendees step, keeping the preselected ticket.
	async goToAttendees(): Promise<void> {
		await this.page.getByRole("button", { name: "Continue to attendees" }).click()
		await expect(this.page.getByRole("heading", { name: "Attendee details" })).toBeVisible()
	}

	// The first ticket is the person registering; their details live in "Your details".
	async fillMyDetails(firstName: string, lastName: string, email: string): Promise<void> {
		// "Your details" comes first, above the tickets that copy it.
		await this.page.getByLabel("First name").first().fill(firstName)
		await this.page.getByLabel("Last name").first().fill(lastName)
		await this.page.getByLabel("Email").first().fill(email)
	}

	async fillAttendeeDetails(name: string, email: string): Promise<void> {
		const [firstName, ...rest] = name.split(" ")
		await this.fillMyDetails(firstName, rest.join(" "), email)
	}

	// Presses Continue through the remaining steps and then the final button.
	async submit(): Promise<void> {
		for (let step = 0; step < 4; step++) {
			const label = (await this.continueButton.textContent()) ?? ""
			await this.continueButton.click()
			if (!ADVANCES.test(label)) return
			await expect(this.continueButton).not.toHaveText(label)
		}
	}

	// Continues to the summary step and pays with the named method.
	async payWith(method: string): Promise<void> {
		for (let step = 0; step < 4; step++) {
			const label = (await this.continueButton.textContent()) ?? ""
			if (!ADVANCES.test(label)) break
			await this.continueButton.click()
			await expect(this.continueButton).not.toHaveText(label)
		}
		// With a single payment method there is nothing to pick on the summary.
		const option = this.page.getByRole("radio", { name: new RegExp(method) })
		if (await option.count()) await option.click()
		await this.continueButton.click()
	}

	async getBookButtonText(): Promise<string | null> {
		return this.continueButton.textContent()
	}

	async expectBookButtonVisible(): Promise<void> {
		await expect(this.continueButton).toBeVisible()
		const text = await this.continueButton.textContent()
		expect(text?.match(/Continue|Book|Pay|Register/i)).toBeTruthy()
	}
}
