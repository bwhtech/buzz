import { expect, Locator, Page } from "@playwright/test";

export class EventProposalPage {
	private page: Page;
	private form: Locator;
	private submitButton: Locator;
	private successBanner: Locator;
	private notFoundBanner: Locator;

	constructor(page: Page) {
		this.page = page;
		this.form = page.locator("form");
		this.submitButton = page.locator('button[type="submit"]').filter({ hasText: /^Submit$/ });
		this.successBanner = page.locator(".bg-surface-green-1");
		this.notFoundBanner = page.locator(".bg-surface-amber-1");
	}

	async goto(): Promise<void> {
		await this.page.goto("/b/event-proposal");
		await this.page.waitForLoadState("networkidle");
	}

	async waitForFormLoad(): Promise<void> {
		await expect(this.form).toBeVisible({ timeout: 15000 });
	}

	getInputByLabel(label: string): Locator {
		return this.page
			.locator(`label:has-text("${label}")`)
			.locator("..")
			.locator("input, textarea, select")
			.first();
	}

	async expectFormVisible(): Promise<void> {
		await expect(this.form).toBeVisible();
	}

	async expectBannerTitle(title: string): Promise<void> {
		await expect(this.page.locator(`h1:has-text("${title}")`)).toBeVisible();
	}

	async expectFieldVisible(label: string): Promise<void> {
		await expect(this.page.locator(`label:has-text("${label}")`)).toBeVisible();
	}

	async expectSubmitButtonVisible(): Promise<void> {
		await expect(this.submitButton).toBeVisible();
	}

	async expectSuccess(): Promise<void> {
		await expect(this.successBanner).toBeVisible({ timeout: 15000 });
	}

	async expectNotFound(): Promise<void> {
		await expect(this.notFoundBanner).toBeVisible({ timeout: 15000 });
	}

	async submit(): Promise<void> {
		await this.submitButton.click();
	}

	async submitAndExpectResponse(): Promise<{ succeeded: boolean; status: number }> {
		const responsePromise = this.page.waitForResponse(
			(resp) => resp.url().includes("submit_event_proposal"),
			{ timeout: 20000 },
		);

		await this.submitButton.click();

		const response = await responsePromise;
		const status = response.status();
		const succeeded = status === 200;

		if (succeeded) {
			await expect(this.successBanner).toBeVisible({ timeout: 15000 });
		}

		return { succeeded, status };
	}
}
