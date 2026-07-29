import { APIRequestContext, BrowserContext, Page, request as playwrightRequest } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { createDoc, docExists, updateDoc } from "./frappe";

const STORAGE_STATE_PATH = "e2e/.auth/user.json";

/**
 * Login via Frappe API (faster than UI login).
 * Sets cookies on the request context for subsequent API calls.
 */
export async function loginViaAPI(
	request: APIRequestContext,
	email = "Administrator",
	password = "admin",
): Promise<void> {
	const response = await request.post("/api/method/login", {
		form: {
			usr: email,
			pwd: password,
		},
	});

	if (!response.ok()) {
		throw new Error(`Login failed: ${response.status()} ${await response.text()}`);
	}
}

/**
 * Login via UI (for testing the login flow itself).
 */
export async function loginViaUI(
	page: Page,
	email = "Administrator",
	password = "admin",
): Promise<void> {
	await page.goto("/login");
	await page.waitForLoadState("networkidle");

	await page.fill('input[data-fieldname="email"]', email);
	await page.fill('input[data-fieldname="password"]', password);
	await page.click('button[type="submit"]');

	// Wait for redirect to desk/app
	await page.waitForURL(/\/(app|desk)/, { timeout: 30000 });
}

/**
 * Logout the current user.
 */
export async function logout(page: Page): Promise<void> {
	await page.goto("/api/method/logout");
	await page.waitForLoadState("networkidle");
}

/**
 * Save authentication state for reuse across tests.
 */
export async function saveAuthState(context: BrowserContext): Promise<void> {
	await context.storageState({ path: STORAGE_STATE_PATH });
}

/**
 * Get the storage state path for authenticated sessions.
 */
export function getStorageStatePath() {
	return STORAGE_STATE_PATH;
}

/**
 * Create a user holding the given roles, or top up the roles if they already exist.
 * Returns the user's name (its email).
 */
export async function createUserWithRoles(
	request: APIRequestContext,
	options: { email: string; firstName: string; password: string; roles: string[] },
): Promise<string> {
	const { email, firstName, password, roles } = options;
	const doc = {
		first_name: firstName,
		new_password: password,
		send_welcome_email: 0,
		enabled: 1,
		roles: roles.map((role) => ({ role })),
	};

	if (await docExists(request, "User", email)) {
		await updateDoc(request, "User", email, doc);
		return email;
	}

	await createDoc(request, "User", { email, user_type: "System User", ...doc });
	return email;
}

/**
 * Log in as the given user in a throwaway context and persist the session to `statePath`,
 * so a Playwright project can run under an identity other than the shared one.
 */
export async function saveLoginState(
	baseURL: string,
	options: { email: string; password: string; statePath: string },
): Promise<void> {
	const context = await playwrightRequest.newContext({ baseURL });
	try {
		await loginViaAPI(context, options.email, options.password);
		fs.mkdirSync(path.dirname(options.statePath), { recursive: true });
		await context.storageState({ path: options.statePath });
	} finally {
		await context.dispose();
	}
}

/**
 * API context under a saved session. Lets a spec running as one user read or assert as
 * another — the shared Administrator state by default.
 */
export async function newApiContext(
	baseURL: string,
	statePath: string = STORAGE_STATE_PATH,
): Promise<APIRequestContext> {
	return playwrightRequest.newContext({ baseURL, storageState: statePath });
}

/**
 * Check if user is logged in by verifying session.
 */
export async function isLoggedIn(request: APIRequestContext): Promise<boolean> {
	try {
		const response = await request.get("/api/method/frappe.auth.get_logged_user");
		if (!response.ok()) return false;

		const data = (await response.json()) as { message?: string };
		return Boolean(data.message && data.message !== "Guest");
	} catch {
		return false;
	}
}
