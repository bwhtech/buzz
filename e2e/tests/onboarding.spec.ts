import { type Page, expect, test } from "@playwright/test"

import { ONBOARDING_USERS } from "../data/onboarding"

const communityName = `Onboarding Club ${Date.now()}`

async function completeProfile(page: Page) {
	await page.goto("/b/onboarding")
	await expect(page.getByRole("heading", { name: "Set up your profile" })).toBeVisible()
	await page.getByRole("button", { name: "Continue" }).click()
	await expect(page.getByRole("heading", { name: "How will you use Buzz?" })).toBeVisible()
}

test.describe("Onboarding as a personal host", () => {
	test.use({ storageState: ONBOARDING_USERS.personal.statePath })

	test("ends with a create-event link that selects the personal team", async ({ page }) => {
		await completeProfile(page)
		await page.getByRole("radio", { name: /Host as myself/ }).click()
		await page.getByRole("button", { name: "Continue" }).click()

		const createEvent = page.getByRole("button", { name: /Create your first event/ })
		await expect(createEvent).toBeEnabled()
		await createEvent.click()

		await expect(page).toHaveURL(/\/b\/manage\/team\/events\/new$/)
		const hostedBy = new RegExp(`${ONBOARDING_USERS.personal.firstName}.*\\(You\\)`)
		await expect(page.getByRole("button", { name: hostedBy })).toBeVisible()
	})
})

test.describe("Onboarding as a community host", () => {
	test.use({ storageState: ONBOARDING_USERS.community.statePath })

	test("creates a community and offers its page", async ({ page }) => {
		await completeProfile(page)
		await page.getByRole("radio", { name: /Create a community/ }).click()
		await page.getByRole("button", { name: "Continue" }).click()

		await page.getByLabel("Community name").fill(communityName)
		const url = page.getByLabel("Community URL")
		await expect(url).toHaveValue(/^onboarding-club-\d+$/)

		const next = page.getByRole("button", { name: "Continue" })
		await url.fill("")
		await expect(next).toBeDisabled()
		await url.fill(`onboarding-club-${Date.now()}`)
		await expect(next).toBeEnabled()
		await next.click()

		await expect(page.getByRole("button", { name: /View community page/ })).toBeVisible()
		await expect(page.getByRole("button", { name: /Create your first event/ })).toBeVisible()
	})
})

test.describe("Onboarding as an attendee", () => {
	test.use({ storageState: ONBOARDING_USERS.attendee.statePath })

	test("skips the fork and lands on the attendee done step", async ({ page }) => {
		await completeProfile(page)
		await page.getByRole("button", { name: "Skip" }).click()

		await expect(page.getByText("Your tickets and bookings live in one place now.")).toBeVisible()
		await expect(page.getByRole("button", { name: /Browse events/ })).toBeVisible()
		await expect(page.getByRole("button", { name: /Create your first event/ })).toHaveCount(0)
	})
})
