import { expect, test } from "@playwright/test";

// Runs under the shared Administrator state, who owns a team and is therefore the one
// member the page is guaranteed to show.
test.describe("Team members", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("/b/manage/events");
		await page.getByRole("link", { name: "Members" }).click();
	});

	test("lists the team from the sidebar", async ({ page }) => {
		await expect(page).toHaveURL(/\/b\/manage\/team\/members$/, { timeout: 15000 });
		await expect(page.getByRole("heading", { name: "Team members", level: 1 })).toBeVisible();
	});

	test("puts the owner first and offers no way to remove them", async ({ page }) => {
		const members = page.getByRole("list", { name: "Team members" }).getByRole("listitem");

		await expect(members.first()).toContainText("Owner", { timeout: 15000 });
		await expect(members.first().getByRole("button", { name: "Member actions" })).toHaveCount(0);
	});
});
