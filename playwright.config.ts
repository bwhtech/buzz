import { defineConfig, devices } from "@playwright/test"

// Auth state file path (added to .gitignore)
const authFile = "e2e/.auth/user.json"
const frontdeskFile = "e2e/.auth/frontdesk.json"
const ticketsAttendeeFile = "e2e/.auth/tickets-attendee.json"

/**
 * Playwright configuration for Buzz E2E tests.
 *
 * Uses the recommended "setup project" pattern for authentication:
 * 1. Setup project runs first and saves auth state to file
 * 2. Other projects depend on setup and reuse the stored auth state
 *
 * @see https://playwright.dev/docs/auth
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
	testDir: "./e2e/tests",
	fullyParallel: false, // Sequential for Frappe state consistency
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: 1, // Single worker for Frappe session management
	reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "html",

	timeout: 60000,
	expect: {
		timeout: 10000,
	},

	/* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
	use: {
		baseURL: process.env.BASE_URL || "http://buzz.test:8000",
		trace: "on-first-retry",
		video: "retain-on-failure",
		screenshot: "only-on-failure",
		actionTimeout: 15000,
		navigationTimeout: 30000,
	},

	/* Configure projects for major browsers */
	projects: [
		{
			name: "setup",
			testMatch: /auth\.setup\.ts/,
		},
		{
			name: "event-setup",
			testMatch: /event\.setup\.ts/,
			use: {
				storageState: authFile,
			},
			dependencies: ["setup"],
		},
		{
			name: "login-modal",
			testMatch: /login-modal\.spec\.ts/,
			use: {
				...devices["Desktop Chrome"],
				storageState: { cookies: [], origins: [] },
			},
			dependencies: ["setup"],
		},
		{
			name: "chromium",
			testIgnore: /guest-booking|custom-forms|event-proposal|login-modal|check-in|tickets|language/,
			use: {
				...devices["Desktop Chrome"],
				storageState: authFile,
			},
			dependencies: ["setup", "event-setup"],
		},
		{
			name: "guest-event-setup",
			testMatch: /guest-event\.setup\.ts/,
			use: {
				storageState: authFile,
			},
			dependencies: ["setup"],
		},
		{
			name: "guest-chromium",
			testMatch: /guest-booking\.spec\.ts/,
			use: {
				...devices["Desktop Chrome"],
			},
			dependencies: ["guest-event-setup"],
		},
		{
			name: "custom-forms-setup",
			testMatch: /custom-forms\.setup\.ts/,
			use: {
				storageState: authFile,
			},
			dependencies: ["setup"],
		},
		{
			name: "custom-forms-chromium",
			testMatch: /custom-forms\.spec\.ts/,
			use: {
				...devices["Desktop Chrome"],
				storageState: authFile,
			},
			dependencies: ["custom-forms-setup"],
		},
		{
			name: "event-proposal-setup",
			testMatch: /event-proposal\.setup\.ts/,
			use: {
				storageState: authFile,
			},
			dependencies: ["setup"],
		},
		{
			name: "event-proposal-chromium",
			testMatch: /event-proposal\.spec\.ts/,
			use: {
				...devices["Desktop Chrome"],
				storageState: authFile,
			},
			dependencies: ["event-proposal-setup"],
		},
		{
			name: "check-in-setup",
			testMatch: /check-in\.setup\.ts/,
			use: {
				storageState: authFile,
			},
			dependencies: ["setup"],
		},
		{
			name: "check-in-chromium",
			testMatch: /check-in\.spec\.ts/,
			use: {
				...devices["Desktop Chrome"],
				storageState: frontdeskFile,
			},
			dependencies: ["check-in-setup"],
		},
		{
			name: "tickets-setup",
			testMatch: /tickets\.setup\.ts/,
			use: {
				storageState: authFile,
			},
			dependencies: ["setup"],
		},
		{
			name: "tickets-chromium",
			testMatch: /tickets\.spec\.ts/,
			use: {
				...devices["Desktop Chrome"],
				storageState: ticketsAttendeeFile,
			},
			dependencies: ["tickets-setup"],
		},
		{
			name: "language-setup",
			testMatch: /language\.setup\.ts/,
			use: {
				storageState: authFile,
			},
			dependencies: ["setup"],
		},
		{
			// The guest specs in here drop the storage state per describe block.
			name: "language-chromium",
			testMatch: /language\.spec\.ts/,
			use: {
				...devices["Desktop Chrome"],
				storageState: authFile,
			},
			dependencies: ["language-setup"],
		},
		{
			name: "offline-payment-setup",
			testMatch: /offline-payment\.setup\.ts/,
			use: {
				storageState: authFile,
			},
			dependencies: ["setup"],
		},
		{
			name: "offline-payment-chromium",
			testMatch: /offline-payment\.spec\.ts/,
			use: {
				...devices["Desktop Chrome"],
				storageState: authFile,
			},
			dependencies: ["offline-payment-setup"],
		},

		// {
		// 	name: "firefox",
		// 	use: { ...devices["Desktop Firefox"] },
		// },

		// {
		// 	name: "webkit",
		// 	use: { ...devices["Desktop Safari"] },
		// },

		/* Test against mobile viewports. */
		// {
		//   name: 'Mobile Chrome',
		//   use: { ...devices['Pixel 5'] },
		// },
		// {
		//   name: 'Mobile Safari',
		//   use: { ...devices['iPhone 12'] },
		// },

		/* Test against branded browsers. */
		// {
		//   name: 'Microsoft Edge',
		//   use: { ...devices['Desktop Edge'], channel: 'msedge' },
		// },
		// {
		//   name: 'Google Chrome',
		//   use: { ...devices['Desktop Chrome'], channel: 'chrome' },
		// },
	],

	/* Run your local dev server before starting the tests */
	// webServer: {
	//   command: 'npm run start',
	//   url: 'http://localhost:3000',
	//   reuseExistingServer: !process.env.CI,
	// },
})
