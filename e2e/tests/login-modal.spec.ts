import { test, expect } from "@playwright/test";

const FRAPPE_USER = process.env.FRAPPE_USER || "Administrator";
const FRAPPE_PASSWORD = process.env.FRAPPE_PASSWORD || "admin";

test.describe("Login Modal", () => {
	test.use({ storageState: { cookies: [], origins: [] } });

	test("email/password login via modal", async ({ page }) => {
		await page.goto("/b");
		await page.waitForLoadState("networkidle");
		await page.getByRole("button", { name: "Log In" }).first().click();
		await expect(page.getByRole("dialog")).toBeVisible();
		await expect(page.getByText("Login to Continue")).toBeVisible();
		await page.getByLabel("Email").fill(FRAPPE_USER);
		await page.getByLabel("Password").fill(FRAPPE_PASSWORD);
		await page.getByRole("button", { name: "Login", exact: true }).click();
		await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });
		await expect(page.getByRole("button", { name: "Log In" })).not.toBeVisible();
	});

	test("shows error for invalid credentials", async ({ page }) => {
		await page.goto("/b");
		await page.waitForLoadState("networkidle");

		await page.getByRole("button", { name: "Log In" }).first().click();
		await expect(page.getByRole("dialog")).toBeVisible();

		await page.getByLabel("Email").fill("wrong@example.com");
		await page.getByLabel("Password").fill("wrongpassword");
		await page.getByRole("button", { name: "Login", exact: true }).click();
		await expect(page.getByRole("dialog")).toBeVisible();
		await expect(page.locator(".bg-surface-red-2")).toBeVisible();
	});
});
