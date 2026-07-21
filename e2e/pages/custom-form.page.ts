import { expect, Locator, Page } from "@playwright/test";

export class CustomFormPage {
	private page: Page;
	private form: Locator;
	private submitButton: Locator;
	private successBanner: Locator;
	private closedBanner: Locator;
	private errorBanner: Locator;

	constructor(page: Page) {
		this.page = page;
		this.form = page.locator("form");
		this.submitButton = page.locator('button[type="submit"]').filter({ hasText: /^Submit$/ });
		this.successBanner = page.locator(".bg-surface-green-1");
		this.closedBanner = page.locator(".bg-surface-orange-1");
		this.errorBanner = page.locator(".bg-surface-amber-1");
	}

	async goto(eventRoute: string, formRoute: string): Promise<void> {
		await this.page.goto(`/b/${eventRoute}/${formRoute}`);
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

	async submit(): Promise<void> {
		await this.submitButton.click();
	}

	async expectFormVisible(): Promise<void> {
		await expect(this.form).toBeVisible();
	}

	async expectFormTitle(title: string): Promise<void> {
		await expect(this.page.locator(`h1:has-text("${title}")`)).toBeVisible();
	}

	async expectFieldVisible(label: string): Promise<void> {
		await expect(this.page.locator(`label:has-text("${label}")`)).toBeVisible();
	}

	async expectSubmitButtonVisible(): Promise<void> {
		await expect(this.submitButton).toBeVisible();
		const text = await this.submitButton.textContent();
		expect(text?.match(/Submit/i)).toBeTruthy();
	}

	async submitAndExpectResponse(): Promise<{ succeeded: boolean; status: number }> {
		const responsePromise = this.page.waitForResponse(
			(resp) => resp.url().includes("submit_custom_form"),
			{ timeout: 20000 },
		);

		await this.submitButton.click();

		const response = await responsePromise;
		const status = response.status();
		const succeeded = status === 200;

		if (succeeded) {
			await expect(this.successBanner).toBeVisible({ timeout: 15000 });
		} else {
			await expect(this.form).toBeVisible();
		}

		return { succeeded, status };
	}

	async expectSuccess(): Promise<void> {
		await expect(this.successBanner).toBeVisible({ timeout: 15000 });
	}

	async expectClosed(): Promise<void> {
		await expect(this.closedBanner).toBeVisible({ timeout: 15000 });
	}

	async expectNotFound(): Promise<void> {
		await expect(this.errorBanner).toBeVisible({ timeout: 15000 });
	}

	async getFieldLabels(): Promise<string[]> {
		const labels = this.page.locator("form label");
		return labels.allTextContents();
	}
}
