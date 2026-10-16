import { expect, test } from "@playwright/test"

import { getList } from "../helpers/frappe"

// Runs against the event event-setup.ts creates, like the other manage specs.
const EVENT_TITLE = "E2E Test Event"
const EVENT_ROUTE = "test-event-e2e"
const PAGE_TITLE = "E2E Additional Page"
const PAGE_ROUTE = "e2e-additional-page"

test("a page added in the dashboard becomes a tab on the event page", async ({ page, request }) => {
	const [event] = await getList<{ name: string }>(request, "Buzz Event", {
		filters: { title: EVENT_TITLE },
	})
	expect(event).toBeTruthy()

	await page.goto(`/b/manage/events/${event.name}/details`)

	await page.getByRole("button", { name: "Add page" }).click()

	const drawer = page.getByRole("dialog")
	await drawer.getByRole("textbox", { name: "Title" }).fill(PAGE_TITLE)
	await drawer.locator('[contenteditable="true"]').click()
	await page.keyboard.type("Written by the additional pages spec.")
	await drawer.getByRole("switch").click()
	await drawer.getByRole("button", { name: "Add page" }).click()
	await expect(drawer).toBeHidden()

	const row = page.locator("section > div", { hasText: PAGE_TITLE })
	await expect(row).toBeVisible()
	await expect(row.getByRole("switch", { name: "Published" })).toBeChecked()

	const tabHref = `/events/${EVENT_ROUTE}/${PAGE_ROUTE}`
	expect(await (await page.request.get(`/events/${EVENT_ROUTE}`)).text()).toContain(tabHref)

	// The row's own switch unpublishes it again, and the tab goes with it.
	await row.getByRole("switch").click()
	await expect
		.poll(async () => (await page.request.get(`/events/${EVENT_ROUTE}`)).text())
		.not.toContain(tabHref)

	await row.getByRole("button", { name: `Delete ${PAGE_TITLE}` }).click()
	await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click()
	await expect(row).toHaveCount(0)
})
