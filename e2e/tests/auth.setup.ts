import { test as setup, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

import { createDoc, getList } from "../helpers/frappe";

const authFile = "e2e/.auth/user.json";
const csrfFile = "e2e/.auth/csrf.json";

setup("authenticate", async ({ page }) => {
	const authDir = path.dirname(authFile);
	if (!fs.existsSync(authDir)) {
		fs.mkdirSync(authDir, { recursive: true });
	}

	// Login via Frappe API using page.request
	const loginResponse = await page.request.post("/api/method/login", {
		form: {
			usr: process.env.FRAPPE_USER || "Administrator",
			pwd: process.env.FRAPPE_PASSWORD || "admin",
		},
	});

	expect(loginResponse.ok()).toBeTruthy();

	// Verify login succeeded by checking current user
	const userResponse = await page.request.get("/api/method/frappe.auth.get_logged_user");
	expect(userResponse.ok()).toBeTruthy();

	const userData = (await userResponse.json()) as { message?: string };
	expect(userData.message).not.toBe("Guest");

	console.log(`✅ Authenticated as: ${userData.message}`);

	// Navigate to app to load frappe context and get CSRF token
	await page.goto("/app");
	await page.waitForLoadState("networkidle");

	// Wait for frappe to initialize and extract CSRF token
	const csrfToken = await page.evaluate(() => {
		return (window as Window & { frappe?: { csrf_token?: string } }).frappe
			?.csrf_token;
	});

	if (csrfToken) {
		// Save CSRF token to file for API helpers to use
		fs.writeFileSync(csrfFile, JSON.stringify({ csrf_token: csrfToken }));
		console.log(`🔐 Saved CSRF token to ${csrfFile}`);
	} else {
		console.warn("⚠️ Could not extract CSRF token from page");
	}

	// Save authentication state
	await page.context().storageState({ path: authFile });
	console.log(`💾 Saved auth state to ${authFile}`);

	// The fixtures omit `team`, which resolves from the acting user's only membership.
	const teams = await getList(page.request, "Buzz Team Membership", {
		filters: { user: userData.message, enabled: 1 },
		limit: 2,
	});

	if (teams.length === 0) {
		await createDoc(page.request, "Buzz Team", { team_name: "E2E Team" });
		console.log("👥 Created E2E Team for the test user");
	}
});
