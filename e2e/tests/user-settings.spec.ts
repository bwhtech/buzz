import { expect, type Page, test } from "@playwright/test"

import { SETTINGS_EMAIL, SETTINGS_FIRST_NAME } from "../data/user-settings"

// Runs as its own user (see user-settings.setup.ts), and every edit is stamped and put back
// through the dialog, so the tests hold in any order.
const unique = (prefix: string) => `${prefix} ${Date.now()}`

// Scoped to the dialog: the events page behind it carries its own labels, and a bare
// getByLabel("Email") also matches an event card's "Open E2E Guest Email OTP" button.
const settings = (page: Page) => page.getByRole("dialog")

async function openSettings(page: Page) {
	await expect(page.getByRole("heading", { name: "Events", level: 1 })).toBeVisible()
	await page.getByLabel("Account menu").click()
	await page.getByRole("button", { name: "Settings" }).click()
	await expect(settings(page).getByRole("heading", { name: "Profile" })).toBeVisible()
}

test.describe("User settings", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("/b/manage/events")
		await openSettings(page)
	})

	test("opens the profile tab on the session user", async ({ page }) => {
		const panel = settings(page)

		await expect(panel.getByLabel("First Name")).toHaveValue(SETTINGS_FIRST_NAME)
		await expect(panel.getByLabel("Email")).toHaveValue(SETTINGS_EMAIL)
		await expect(panel.getByRole("button", { name: "Save" })).toHaveCount(0)
	})

	test("saves a new first name and updates the sidebar", async ({ page }) => {
		const panel = settings(page)
		const firstName = panel.getByLabel("First Name")
		const save = panel.getByRole("button", { name: "Save" })
		const edited = unique("Buzz")

		await firstName.fill(edited)
		await expect(save).toBeEnabled()
		await save.click()

		// The sidebar reads full_name, which the server derives on save.
		await expect(page.getByLabel("Account menu")).toContainText(edited)

		await firstName.fill(SETTINGS_FIRST_NAME)
		await save.click()
		await expect(save).toHaveCount(0)
	})

	test("keeps a saved bio across a reload", async ({ page }) => {
		const bio = settings(page).getByLabel("Bio")
		const edited = unique("Runs the conference.")

		await bio.fill(edited)
		await settings(page).getByRole("button", { name: "Save" }).click()
		await expect(settings(page).getByRole("button", { name: "Save" })).toHaveCount(0)

		await page.reload()
		await openSettings(page)
		await expect(settings(page).getByLabel("Bio")).toHaveValue(edited)

		await settings(page).getByLabel("Bio").fill("")
		await settings(page).getByRole("button", { name: "Save" }).click()
		await expect(settings(page).getByRole("button", { name: "Save" })).toHaveCount(0)
	})

	test("lists the user's teams and opens one to manage", async ({ page }) => {
		const panel = settings(page)

		await panel.getByRole("tab", { name: "Teams" }).click()
		await expect(panel.getByRole("heading", { name: "Your Teams" })).toBeVisible()

		const teams = panel.getByRole("list", { name: "Your teams" }).getByRole("listitem")
		await expect(teams.first()).toContainText("members", { timeout: 15000 })

		await teams.first().getByRole("button").click()

		// The Manager role can read the roster but not change it.
		const members = panel.getByRole("list", { name: "Team members" }).getByRole("listitem")
		await expect(members.first()).toContainText("Owner", { timeout: 15000 })
		await expect(panel.getByRole("button", { name: "Add member" })).toHaveCount(0)

		await panel.getByRole("button", { name: "Back to teams" }).click()
		await expect(panel.getByRole("heading", { name: "Your Teams" })).toBeVisible()
	})
})
