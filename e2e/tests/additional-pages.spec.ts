import { expect, test } from "@playwright/test"

import { getList } from "../helpers/frappe"

// Runs against the event event-setup.ts creates, like the other manage specs.
const EVENT_TITLE = "E2E Test Event"
const EVENT_ROUTE = "test-event-e2e"
const PAGE_TITLE = "E2E Additional Page"
const CONTENT = "Written by the additional pages spec."

test("a page added in the dashboard becomes a tab on the event page", async ({ page, request }) => {
	const [event] = await getList<{ name: string }>(request, "Buzz Event", {
		filters: { title: EVENT_TITLE },
	})
	expect(event).toBeTruthy()

	await page.goto(`/b/manage/events/${event.name}/details`)

	await page.getByRole("button", { name: "Blank page" }).click()

	const drawer = page.getByRole("dialog")
	await drawer.getByRole("textbox", { name: "Title" }).fill(PAGE_TITLE)
	await drawer.locator('[contenteditable="true"]').click()
	await page.keyboard.type(CONTENT)
	await drawer.getByRole("switch", { name: "Show on event page" }).click()
	await drawer.getByRole("button", { name: "Add page" }).click()
	await expect(drawer).toBeHidden()

	const row = page.getByRole("listitem").filter({ hasText: PAGE_TITLE })
	await expect(row).toBeVisible()
	await expect(row.getByText("Hidden")).toBeHidden()

	// The tab sits on the event page itself, so opening it shows its words without a
	// navigation and the content is hidden until the tab is picked.
	const eventUrl = `/events/${EVENT_ROUTE}`
	await page.goto(eventUrl)
	await expect(page.getByText(CONTENT)).toBeHidden()
	await page.locator("label.tab", { hasText: PAGE_TITLE }).click()
	await expect(page.getByText(CONTENT)).toBeVisible()
	await expect(page).toHaveURL(eventUrl)

	// The row's own eye button unpublishes it again, and the tab goes with it.
	await page.goto(`/b/manage/events/${event.name}/details`)
	await row.getByRole("button", { name: "Hide from event page" }).click()
	await expect.poll(async () => (await page.request.get(eventUrl)).text()).not.toContain(PAGE_TITLE)

	await row.getByRole("button", { name: `Actions for ${PAGE_TITLE}` }).click()
	await page.getByRole("menuitem", { name: "Delete" }).click()
	await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click()
	await expect(row).toHaveCount(0)
})
