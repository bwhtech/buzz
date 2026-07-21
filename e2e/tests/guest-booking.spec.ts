import { test, expect } from "@playwright/test";
import { BookingPage } from "../pages";

// Unique suffix per run to avoid rate limits
const uid = Date.now();

test.describe("Guest Booking UX", () => {
	test("guest details auto-fill to Attendee 1", async ({ page }) => {
		const bookingPage = new BookingPage(page);
		await bookingPage.goto("guest-no-otp-e2e");
		await bookingPage.waitForFormLoad();

		await page.locator('input[placeholder="Enter your first name"]').fill("Test");
		await page.locator('input[placeholder="Enter your last name"]').fill("Guest");
		await page.locator('input[placeholder="Enter your email"]').fill("test@example.com");
		await page.locator('input[placeholder="Enter your email"]').blur();

		await expect(page.locator('input[placeholder="Enter first name"]').first()).toHaveValue("Test");
		await expect(page.locator('input[placeholder="Enter last name"]').first()).toHaveValue("Guest");
		await expect(page.locator('input[placeholder="Enter email address"]').first()).toHaveValue("test@example.com");
	});
});

test.describe("Guest Booking", () => {
	test("guest booking without OTP", async ({ page }) => {
		const email = `guest-no-otp-${uid}@test.com`;
		const bookingPage = new BookingPage(page);
		await bookingPage.goto("guest-no-otp-e2e");
		await bookingPage.waitForFormLoad();

		await page.locator('input[placeholder="Enter your first name"]').fill("Test");
		await page.locator('input[placeholder="Enter your last name"]').fill("Guest");
		await page.locator('input[placeholder="Enter your email"]').fill(email);
		await page.locator('input[placeholder="Enter your email"]').blur();

		await bookingPage.submit();

		await expect(page.getByText("Booking Confirmed")).toBeVisible({ timeout: 30000 });
	});

	test("guest booking with Email OTP", async ({ page }) => {
		const email = `guest-email-otp-${uid}@test.com`;
		const bookingPage = new BookingPage(page);
		await bookingPage.goto("guest-email-otp-e2e");
		await bookingPage.waitForFormLoad();

		await page.locator('input[placeholder="Enter your first name"]').fill("Test");
		await page.locator('input[placeholder="Enter your last name"]').fill("Guest Email");
		await page.locator('input[placeholder="Enter your email"]').fill(email);
		await page.locator('input[placeholder="Enter your email"]').blur();

		const otpResponsePromise = page.waitForResponse(
			(resp) => resp.url().includes("send_guest_booking_otp") && resp.status() === 200,
		);

		await bookingPage.submit();

		const otpResponse = await otpResponsePromise;
		const otpData = (await otpResponse.json()) as { message?: { otp?: string } };
		const otp = otpData.message?.otp;
		expect(otp).toBeTruthy();

		await expect(page.getByText("Verify Your Email")).toBeVisible({ timeout: 10000 });

		await page.locator('input[placeholder="123456"]').fill(otp!);
		await page.getByRole("button", { name: "Verify & Book" }).click();

		await expect(page.getByText("Booking Confirmed")).toBeVisible({ timeout: 30000 });
	});

	test("guest booking with Phone OTP", async ({ page }) => {
		const email = `guest-phone-otp-${uid}@test.com`;
		const phone = `9${uid.toString().slice(-9)}`;
		const bookingPage = new BookingPage(page);
		await bookingPage.goto("guest-phone-otp-e2e");
		await bookingPage.waitForFormLoad();

		await page.locator('input[placeholder="Enter your first name"]').fill("Test");
		await page.locator('input[placeholder="Enter your last name"]').fill("Guest Phone");
		await page.locator('input[placeholder="Enter your email"]').fill(email);
		await page.locator('input[placeholder="Enter your email"]').blur(); // triggers auto-fill
		await page.locator('input[placeholder="Enter your phone number"]').fill(phone);

		const otpResponsePromise = page.waitForResponse(
			(resp) => resp.url().includes("send_guest_booking_otp") && resp.status() === 200,
		);

		await bookingPage.submit();

		const otpResponse = await otpResponsePromise;
		const otpData = (await otpResponse.json()) as { message?: { otp?: string } };
		const otp = otpData.message?.otp;
		expect(otp).toBeTruthy();

		await expect(page.getByText("Verify Your Phone")).toBeVisible({ timeout: 10000 });

		await page.locator('input[placeholder="123456"]').fill(otp!);
		await page.getByRole("button", { name: "Verify & Book" }).click();

		await expect(page.getByText("Booking Confirmed")).toBeVisible({ timeout: 30000 });
	});
});
