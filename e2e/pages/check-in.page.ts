import { expect, Locator, Page } from "@playwright/test";

export class CheckInPage {
	private page: Page;
	accessDeniedMessage: Locator;
	manualTicketInput: Locator;
	lastScanResult: Locator;
	ticketModal: Locator;
	private checkButton: Locator;
	private checkInButton: Locator;

	constructor(page: Page) {
		this.page = page;
		this.accessDeniedMessage = page.getByText("Access Denied");
		this.manualTicketInput = page.getByPlaceholder("Enter ticket ID manually");
		this.checkButton = page.getByRole("button", { name: "Check", exact: true });
		this.ticketModal = page.getByRole("dialog");
		this.checkInButton = page.getByRole("button", { name: "Check In", exact: true });
		this.lastScanResult = page.getByText("Last Scan Result");
	}

	async goto(eventName?: string): Promise<void> {
		await this.page.goto(eventName ? `/b/check-in/${eventName}` : "/b/check-in");
		await this.page.waitForLoadState("networkidle");
	}

	async submitTicketId(ticketId: string): Promise<void> {
		await this.manualTicketInput.fill(ticketId);
		await this.checkButton.click();
	}

	/**
	 * Clicks Check In and waits for the request to land. The "Last Scan Result" panel is not a
	 * usable signal — it is already on screen from the preceding validate call.
	 */
	async confirmCheckIn(): Promise<void> {
		const recorded = this.page.waitForResponse(
			(response) => response.url().includes("checkin_ticket") && response.status() === 200,
		);
		await this.checkInButton.click();
		await recorded;
		await expect(this.ticketModal).toBeHidden();
	}

	async expectScannerVisible(): Promise<void> {
		await expect(this.manualTicketInput).toBeVisible({ timeout: 15000 });
		await expect(this.accessDeniedMessage).toBeHidden();
	}

	async expectAccessDenied(): Promise<void> {
		await expect(this.accessDeniedMessage).toBeVisible({ timeout: 15000 });
	}

	async expectTicketModal(attendeeName: string): Promise<void> {
		await expect(this.ticketModal).toBeVisible({ timeout: 15000 });
		await expect(this.ticketModal.getByText(attendeeName)).toBeVisible();
	}

	async expectToast(message: string | RegExp): Promise<void> {
		await expect(this.page.getByText(message).first()).toBeVisible({ timeout: 15000 });
	}
}
