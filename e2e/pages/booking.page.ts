import { expect, Locator, Page } from "@playwright/test";

export class BookingPage {
	private page: Page;
	attendeeNameInput: Locator;
	attendeeEmailInput: Locator;
	ticketTypeSelect: Locator;
	addOnCheckboxes: Locator;
	private bookButton: Locator;
	private addAttendeeButton: Locator;
	private bookingForm: Locator;
	private summarySection: Locator;

	constructor(page: Page) {
		this.page = page;

		// Form elements
		this.attendeeNameInput = page
			.locator('input[placeholder*="name" i], input[name*="name" i]')
			.first();
		this.attendeeEmailInput = page
			.locator('input[type="email"], input[placeholder*="email" i]')
			.first();
		this.ticketTypeSelect = page.locator('select, [data-testid="ticket-type"]').first();

		// Add-ons
		this.addOnCheckboxes = page.locator('input[type="checkbox"]');

		// Buttons
		this.bookButton = page.locator('button[type="submit"]');
		this.addAttendeeButton = page.locator('button:has-text("Add Another Attendee")');

		// Sections
		this.bookingForm = page.locator("form");
		this.summarySection = page.locator('[class*="summary" i]').first();
	}

	// Navigate to the booking page for a specific event.
	async goto(eventRoute: string): Promise<void> {
		await this.page.goto(`/b/register/${eventRoute}`);
		await this.page.waitForLoadState("networkidle");
	}

	// Wait for the booking form to fully load.
	async waitForFormLoad(): Promise<void> {
		await expect(this.bookingForm).toBeVisible({ timeout: 15000 });
	}

	// Fill in attendee details.
	async fillAttendeeDetails(name: string, email: string): Promise<void> {
		await this.attendeeNameInput.fill(name);
		await this.attendeeEmailInput.fill(email);
	}

	// Select a ticket type by its visible text.
	async selectTicketType(ticketTitle: string): Promise<void> {
		const ticketOption = this.page.locator(`text=${ticketTitle}`).first();
		if (await ticketOption.isVisible()) {
			await ticketOption.click();
		}
	}

	/**
	 * Toggle an add-on by its title.
	 */
	async toggleAddOn(addOnTitle: string): Promise<void> {
		const addOnLabel = this.page.locator(`label:has-text("${addOnTitle}")`).first();
		if (await addOnLabel.isVisible()) {
			await addOnLabel.click();
		}
	}

	// Add another attendee to the booking.
	async addAnotherAttendee(): Promise<void> {
		await this.addAttendeeButton.click();
	}

	// Submit the booking form.
	async submit(): Promise<void> {
		await this.bookButton.click();
	}

	// Get the booking button text.
	async getBookButtonText(): Promise<string | null> {
		return this.bookButton.textContent();
	}

	//  Assert that the booking form is visible.
	async expectFormVisible(): Promise<void> {
		await expect(this.bookingForm).toBeVisible();
	}

	// Assert that ticket types are displayed.
	async expectTicketTypesVisible(): Promise<void> {
		// Check for any ticket-related content
		const ticketContent = this.page
			.locator('[class*="ticket"], select, input[type="radio"]')
			.first();
		await expect(ticketContent).toBeVisible({ timeout: 10000 });
	}

	// Assert that add-ons are displayed.
	async expectAddOnsVisible(): Promise<void> {
		const addOnCount = await this.addOnCheckboxes.count();
		expect(addOnCount).toBeGreaterThan(0);
	}

	// Assert that the book button is visible with expected text.
	async expectBookButtonVisible(): Promise<void> {
		await expect(this.bookButton).toBeVisible();
		const text = await this.bookButton.textContent();
		expect(text?.match(/Book|Pay|Register/i)).toBeTruthy();
	}

	// Get the count of attendee forms on the page.
	async getAttendeeCount(): Promise<number> {
		const attendeeForms = this.page.locator('[class*="attendee"], [class*="Attendee"]');
		return await attendeeForms.count();
	}
}
