import { expect, test } from "@playwright/test";

// Runs under the shared Administrator state, whose team hosts the event seeded by
// event.setup.ts — the one card guaranteed to carry a Manage button.
test.describe("Event workspace", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("/b/manage/events");
		await page.getByRole("link", { name: "Manage" }).first().click();
	});

	test("opens the event on its details section", async ({ page }) => {
		await expect(page).toHaveURL(/\/b\/manage\/events\/\d+\/details$/, { timeout: 15000 });
		await expect(page.getByText("Work in progress")).toBeVisible();
	});

	test("swaps the sidebar for the event's own destinations", async ({ page }) => {
		for (const label of ["Back", "Details", "Attendees", "Talks"]) {
			await expect(page.getByRole("link", { name: label })).toBeVisible({ timeout: 15000 });
		}
		await expect(page.getByRole("link", { name: "My Tickets" })).toHaveCount(0);
	});

	test("moves between sections", async ({ page }) => {
		await page.getByRole("link", { name: "Talks" }).click();

		await expect(page).toHaveURL(/\/b\/manage\/events\/\d+\/talks$/);
		await expect(page.getByText("Work in progress")).toBeVisible();
	});

	test("leaves the workspace through the back item", async ({ page }) => {
		await page.getByRole("link", { name: "Back" }).click();

		await expect(page).toHaveURL(/\/b\/manage\/events$/, { timeout: 15000 });
		await expect(page.getByRole("heading", { name: "Events", level: 1 })).toBeVisible();
	});
});

// A team's own events are all manageable, so those cards drop the button and become
// the link themselves.
test.describe("Team events card", () => {
	test("opens the workspace on click, with no Manage button of its own", async ({ page }) => {
		await page.goto("/b/manage/events");
		await page.getByRole("link", { name: "Events", exact: true }).click();
		await expect(page).toHaveURL(/\/b\/manage\/team\/events$/, { timeout: 15000 });

		// Keyed on the href, not a title: which events the team owns varies by site.
		const card = page.locator('a[href^="/b/manage/events/"]').first();
		await expect(card).toBeVisible({ timeout: 15000 });
		await expect(page.getByRole("link", { name: "Manage" })).toHaveCount(0);
		await card.click();

		await expect(page).toHaveURL(/\/b\/manage\/events\/\d+\/details$/);
	});
});
