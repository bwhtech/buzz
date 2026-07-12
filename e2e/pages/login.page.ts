import { expect, Locator, Page } from "@playwright/test";

/**
 * Page Object for the Frappe login page.
 */
export class LoginPage {
	private page: Page;
	private emailInput: Locator;
	private passwordInput: Locator;
	private submitButton: Locator;
	private errorMessage: Locator;

	constructor(page: Page) {
		this.page = page;

		// Frappe login page selectors
		this.emailInput = page.locator("#login_email");
		this.passwordInput = page.locator("#login_password");
		this.submitButton = page.getByRole("button", { name: "Continue" });
		this.errorMessage = page.locator(".msgprint, .alert-danger").first();
	}

	/**
	 * Navigate to the login page.
	 */
	async goto(): Promise<void> {
		await this.page.goto("/login");
		await this.page.waitForLoadState("networkidle");
	}

	/**
	 * Fill in the login form with credentials.
	 */
	async fillCredentials(email: string, password: string): Promise<void> {
		await this.emailInput.fill(email);
		await this.passwordInput.fill(password);
	}

	/**
	 * Submit the login form.
	 */
	async submit(): Promise<void> {
		await this.submitButton.click();
	}

	/**
	 * Perform a complete login.
	 */
	async login(email = "Administrator", password = "admin"): Promise<void> {
		await this.goto();
		await this.fillCredentials(email, password);
		await this.submit();
		await this.page.waitForURL(/\/(app|desk|buzz)/, { timeout: 30000 });
	}

	/**
	 * Assert that login failed with an error.
	 */
	async expectLoginError(): Promise<void> {
		await expect(this.errorMessage).toBeVisible();
	}

	/**
	 * Assert that we're on the login page.
	 */
	async expectToBeOnLoginPage(): Promise<void> {
		await expect(this.page).toHaveURL(/.*login.*/);
	}
}
