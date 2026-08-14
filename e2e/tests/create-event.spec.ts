import { expect, test } from "@playwright/test";

// The create page and the event details page share EventBanner, so this is the guard
// that the extraction did not cost the create form its banner.
test.describe("Create event", () => {
	test("offers a banner, a title and a way to save", async ({ page }) => {
		await page.goto("/b/manage/events");
		await page.getByRole("link", { name: "Events", exact: true }).click();
		await page.getByRole("link", { name: "Create Event" }).click();

		await expect(page).toHaveURL(/\/b\/manage\/team\/events\/new$/, { timeout: 15000 });
		await expect(page.getByRole("button", { name: "Add a banner" })).toBeVisible();
		await expect(page.getByRole("textbox", { name: "Event title" })).toBeVisible();
		// Nothing is filled in yet, so the page must not offer to create anything.
		await expect(page.getByRole("button", { name: "Create event" })).toBeDisabled();
	});
});
