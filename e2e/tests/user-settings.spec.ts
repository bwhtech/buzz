import { expect, type Page, test } from "@playwright/test"

// Nothing here hardcodes who the session user is or what their profile holds: CI
// signs in as FRAPPE_USER, and the whole chromium project shares that account.
// Every test reads the saved value, edits it to something unique, and puts it
// back through the same dialog.
const unique = (prefix: string) => `${prefix} ${Date.now()}`

async function openSettings(page: Page) {
	await page.getByRole("heading", { name: "Events", level: 1 }).waitFor()
	await page.getByLabel("Account menu").click()
	await page.getByRole("button", { name: "Settings" }).click()
	await expect(page.getByRole("heading", { name: "Profile" })).toBeVisible()
}

test.describe("User settings", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("/b/manage/events")
		await openSettings(page)
	})

	test("opens the profile tab with the saved profile and nothing to save", async ({ page }) => {
		await expect(page.getByLabel("First Name")).not.toHaveValue("")
		await expect(page.getByLabel("Email")).not.toHaveValue("")
		await expect(page.getByRole("button", { name: "Save" })).toHaveCount(0)
	})

	test("saves a new first name and updates the sidebar", async ({ page }) => {
		const firstName = page.getByLabel("First Name")
		const save = page.getByRole("button", { name: "Save" })
		const original = await firstName.inputValue()
		const edited = unique("Buzz")

		await firstName.fill(edited)
		await expect(save).toBeEnabled()
		await save.click()

		// The sidebar reads full_name, which the server derives on save.
		await expect(page.getByLabel("Account menu")).toContainText(edited)

		await firstName.fill(original)
		await save.click()
		await expect(save).toHaveCount(0)
	})

	test("keeps a saved bio across a reload", async ({ page }) => {
		const bio = page.getByLabel("Bio")
		const save = page.getByRole("button", { name: "Save" })
		const original = await bio.inputValue()
		const edited = unique("Runs the conference.")

		await bio.fill(edited)
		await save.click()
		await expect(save).toHaveCount(0)

		await page.reload()
		await openSettings(page)
		await expect(page.getByLabel("Bio")).toHaveValue(edited)

		await page.getByLabel("Bio").fill(original)
		await page.getByRole("button", { name: "Save" }).click()
		await expect(page.getByRole("button", { name: "Save" })).toHaveCount(0)
	})
})
