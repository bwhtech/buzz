import { type Page, expect, test } from "@playwright/test";

// Enabled by language.setup.ts.
const TARGET_LANGUAGE = "de";

const switcher = (page: Page) => page.getByTestId("language-switcher");
const activeLanguage = (page: Page) => switcher(page).locator("span[lang]");

/**
 * Pick a language from the open dropdown.
 *
 * The row itself is rendered by frappe-ui, so the test id sits on the label
 * span the switcher supplies. Clicking it selects the row it belongs to.
 */
async function chooseLanguage(page: Page, languageCode: string) {
	await switcher(page).click();
	await expect(page.locator('[data-slot="content"]')).toBeVisible();
	await page.getByTestId(`language-option-${languageCode}`).click();
}

async function preferredLanguageCookie(page: Page): Promise<string | undefined> {
	const cookies = await page.context().cookies();
	return cookies.find((cookie) => cookie.name === "preferred_language")?.value;
}

test.describe("Language switcher — guest", () => {
	test.use({ storageState: { cookies: [], origins: [] } });

	test("switching language stores a cookie instead of calling the account API", async ({
		page,
	}) => {
		// Every guest shares the one `Guest` User, so the endpoint that writes to
		// it is not whitelisted for guests — it used to return a PermissionError.
		const userLanguageCalls: string[] = [];
		page.on("request", (request) => {
			if (request.url().includes("update_user_language")) {
				userLanguageCalls.push(request.url());
			}
		});

		await page.goto("/b");
		await page.waitForLoadState("networkidle");

		await expect(switcher(page)).toBeVisible();
		await chooseLanguage(page, TARGET_LANGUAGE);

		await expect(activeLanguage(page)).toHaveAttribute("lang", TARGET_LANGUAGE);
		expect(await preferredLanguageCookie(page)).toBe(TARGET_LANGUAGE);
		expect(userLanguageCalls).toEqual([]);
	});

	test("the chosen language survives a fresh page load", async ({ page }) => {
		await page.goto("/b");
		await page.waitForLoadState("networkidle");

		await chooseLanguage(page, TARGET_LANGUAGE);
		await expect(activeLanguage(page)).toHaveAttribute("lang", TARGET_LANGUAGE);

		await page.goto("/b");
		await expect(activeLanguage(page)).toHaveAttribute("lang", TARGET_LANGUAGE);
	});

	test("?lang pins the language and disappears from the URL", async ({ page }) => {
		await page.goto(`/b?lang=${TARGET_LANGUAGE}`);

		await expect(activeLanguage(page)).toHaveAttribute("lang", TARGET_LANGUAGE);
		expect(await preferredLanguageCookie(page)).toBe(TARGET_LANGUAGE);
		// Left in place it would re-pin the language on every later reload.
		await expect
			.poll(() => new URL(page.url()).searchParams.has("lang"))
			.toBe(false);
	});

	test("an unknown ?lang value is never written to the cookie", async ({ page }) => {
		await page.goto("/b?lang=not-a-language");
		await page.waitForLoadState("networkidle");

		await expect(switcher(page)).toBeVisible();
		await expect(activeLanguage(page)).not.toHaveAttribute("lang", "not-a-language");
		expect(await preferredLanguageCookie(page)).toBeUndefined();
		await expect
			.poll(() => new URL(page.url()).searchParams.has("lang"))
			.toBe(false);
	});
});

test.describe("Language switcher — logged in", () => {
	test("?lang does not rewrite a saved language preference", async ({ page }) => {
		await page.goto(`/b?lang=${TARGET_LANGUAGE}`);
		await page.waitForLoadState("networkidle");

		// The user's own preference wins; the parameter is still stripped.
		await expect(switcher(page)).toBeVisible();
		await expect(activeLanguage(page)).not.toHaveAttribute("lang", TARGET_LANGUAGE);
		expect(await preferredLanguageCookie(page)).toBeUndefined();
		await expect
			.poll(() => new URL(page.url()).searchParams.has("lang"))
			.toBe(false);
	});
});
