import { test, expect } from "@playwright/test";
import { LoginPage } from "../pages";
import { isLoggedIn } from "../helpers";

/**
 * Tests for authentication that already have auth state from setup.
 */
test.describe("Authentication - Pre-authenticated", () => {
	test("should access buzz when authenticated", async ({ page }) => {
		// Already authenticated via setup project
		await page.goto("/b/");
		await page.waitForLoadState("networkidle");

		// Should not be redirected to login
		await expect(page).not.toHaveURL(/.*login.*/);
	});

	test("should verify session via API", async ({ request }) => {
		// Already authenticated via setup project
		const loggedIn = await isLoggedIn(request);
		expect(loggedIn).toBe(true);
	});
});

/**
 * Tests for authentication that need fresh (unauthenticated) state.
 * Uses storageState reset to clear any auth cookies.
 */
test.describe("Authentication - Fresh state", () => {
	// Reset storage state to test without authentication
	test.use({ storageState: { cookies: [], origins: [] } });

	test("should login via UI", async ({ page }) => {
		const loginPage = new LoginPage(page);

		await loginPage.login(process.env.FRAPPE_USER || "Administrator", process.env.FRAPPE_PASSWORD || "admin");

		// Should be redirected away from login
		await expect(page).not.toHaveURL(/.*login.*/);
	});

	test("should show error for invalid credentials", async ({ page }) => {
		const loginPage = new LoginPage(page);

		await loginPage.goto();
		await loginPage.fillCredentials("invalid@example.com", "wrongpassword");
		await loginPage.submit();

		// Should stay on login page
		await loginPage.expectToBeOnLoginPage();
	});

	test("should show login button when not authenticated", async ({ page }) => {
		await page.goto("/b");
		await page.waitForLoadState("networkidle");

		await expect(page.getByRole("button", { name: "Log In" }).first()).toBeVisible();
	});
});
