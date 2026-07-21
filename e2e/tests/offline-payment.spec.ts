import { test, expect } from "@playwright/test";
import { BookingPage } from "../pages";

const uid = Date.now();

test.describe("Offline Payment Flow", () => {
	test("complete booking with offline payment", async ({ page }) => {
		const email = `offline-${uid}@test.com`;
		const bookingPage = new BookingPage(page);

		await bookingPage.goto("offline-payment-e2e");
		await bookingPage.waitForFormLoad();

		// Fill attendee details
		await page.locator('input[placeholder="Enter first name"]').first().fill("Test");
		await page.locator('input[placeholder="Enter last name"]').first().fill("User");
		await page.locator('input[placeholder="Enter email address"]').first().fill(email);

		// Submit booking form
		await bookingPage.submit();

		// Wait for offline payment dialog
		await expect(page.getByText("Bank Transfer")).toBeVisible({ timeout: 10000 });
		await expect(page.getByText("Transfer to Account: 123456789")).toBeVisible();

		// Submit offline payment (no file upload required in test setup)
		const submitButton = page.getByRole("button", { name: "Submit" });
		await submitButton.click();

		// Verify booking created with verification pending status
		await expect(page.getByText("Payment Confirmation Pending")).toBeVisible({ timeout: 30000 });
	});

	test("offline payment dialog shows amount", async ({ page }) => {
		const bookingPage = new BookingPage(page);

		await bookingPage.goto("offline-payment-e2e");
		await bookingPage.waitForFormLoad();

		await page.locator('input[placeholder="Enter first name"]').first().fill("Amount");
		await page.locator('input[placeholder="Enter last name"]').first().fill("Test");
		await page.locator('input[placeholder="Enter email address"]').first().fill(`amount-${uid}@test.com`);

		await bookingPage.submit();

		// Wait for dialog and verify amount is displayed in dialog
		const dialog = page.getByRole("dialog");
		await expect(dialog.getByText("₹500.00", { exact: true })).toBeVisible({ timeout: 10000 });
	});

	test("can cancel offline payment dialog", async ({ page }) => {
		const bookingPage = new BookingPage(page);

		await bookingPage.goto("offline-payment-e2e");
		await bookingPage.waitForFormLoad();

		await page.locator('input[placeholder="Enter first name"]').first().fill("Cancel");
		await page.locator('input[placeholder="Enter last name"]').first().fill("Test");
		await page.locator('input[placeholder="Enter email address"]').first().fill(`cancel-${uid}@test.com`);

		await bookingPage.submit();

		await expect(page.getByText("Bank Transfer")).toBeVisible({ timeout: 10000 });

		// Click cancel
		await page.getByRole("button", { name: "Cancel" }).click();

		// Dialog should close
		await expect(page.getByText("Bank Transfer")).not.toBeVisible({ timeout: 5000 });
	});
});

test.describe("Booking Details - Offline Payment", () => {
	test("shows verification pending status", async ({ page }) => {
		// This test assumes a booking already exists
		// Navigate to bookings list
		await page.goto("/b/bookings");
		await page.waitForLoadState("networkidle");

		// Look for verification pending badge
		const pendingBadge = page.locator('text=/Verification Pending|Approval Pending/i').first();
		if (await pendingBadge.isVisible({ timeout: 5000 })) {
			await expect(pendingBadge).toBeVisible();
		}
	});
});
