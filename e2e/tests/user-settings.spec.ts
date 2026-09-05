import { expect, test } from "@playwright/test"

import { updateDoc } from "../helpers"

// Runs under the shared Administrator state, so the edit is made to that user and
// put back afterwards — every other spec in this project reads the same name.
const ORIGINAL_FIRST_NAME = "Administrator"
const EDITED_FIRST_NAME = "Buzz Admin"
const EDITED_BIO = "Runs the conference."

test.describe("User settings", () => {
	test.afterAll(async ({ request }) => {
		await updateDoc(request, "User", "Administrator", {
			first_name: ORIGINAL_FIRST_NAME,
			bio: "",
		})
	})

	test.beforeEach(async ({ page }) => {
		await page.goto("/b/manage/events")
		await expect(page.getByRole("heading", { name: "Events", level: 1 })).toBeVisible()
		await page.getByLabel("Account menu").click()
		await page.getByRole("button", { name: "Settings" }).click()
	})

	test("opens the profile tab with the current name filled in", async ({ page }) => {
		await expect(page.getByRole("heading", { name: "Profile" })).toBeVisible()
		await expect(page.getByLabel("First Name")).toHaveValue(ORIGINAL_FIRST_NAME)
		await expect(page.getByRole("button", { name: "Save" })).toHaveCount(0)
	})

	test("saves the profile and updates the sidebar", async ({ page }) => {
		await page.getByLabel("First Name").fill(EDITED_FIRST_NAME)
		await page.getByLabel("Bio").fill(EDITED_BIO)

		const save = page.getByRole("button", { name: "Save" })
		await expect(save).toBeEnabled()
		await save.click()

		await expect(page.getByText("Profile updated")).toBeVisible()

		// The sidebar reads full_name, which the server derives on save.
		await page.keyboard.press("Escape")
		await expect(page.getByLabel("Account menu")).toContainText(EDITED_FIRST_NAME)
	})

	test("keeps the saved bio across a reload", async ({ page }) => {
		await page.getByLabel("Bio").fill(EDITED_BIO)
		await page.getByRole("button", { name: "Save" }).click()
		await expect(page.getByText("Profile updated")).toBeVisible()

		await page.reload()
		await page.getByLabel("Account menu").click()
		await page.getByRole("button", { name: "Settings" }).click()

		await expect(page.getByLabel("Bio")).toHaveValue(EDITED_BIO)
	})
})
