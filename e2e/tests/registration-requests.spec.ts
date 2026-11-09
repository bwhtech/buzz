import { expect, test } from "@playwright/test"

import { REQUESTER, REQUESTS_EVENT_ROUTE } from "../data/registration-requests"
import { newApiContext } from "../helpers/auth"
import { getList } from "../helpers/frappe"
import { BookingPage } from "../pages"

async function findEvent(baseURL: string) {
	const api = await newApiContext(baseURL)
	const [event] = await getList<{ name: string }>(api, "Buzz Event", {
		filters: { route: REQUESTS_EVENT_ROUTE },
		limit: 1,
	})
	await api.dispose()
	return event.name
}

test("guest requests a free ticket, the organizer approves it, and the booking is confirmed", async ({
	page,
	browser,
	baseURL,
}) => {
	const eventId = await findEvent(baseURL!)

	// The guest signs in on a context of their own, so the organizer keeps the shared session.
	const guestContext = await browser.newContext({ storageState: REQUESTER.statePath })
	const guestPage = await guestContext.newPage()
	const bookingPage = new BookingPage(guestPage)

	await bookingPage.goto(REQUESTS_EVENT_ROUTE)
	await bookingPage.waitForFormLoad()
	await bookingPage.goToAttendees()
	await bookingPage.fillMyDetails(REQUESTER.name, "E2E", REQUESTER.email)
	await expect(guestPage.getByRole("button", { name: "Request to join" })).toBeVisible()
	await bookingPage.submit()

	await expect(guestPage).toHaveURL(/\/booking-success\/.+/)
	await expect(guestPage.getByText("Request received").first()).toBeVisible({ timeout: 30000 })

	await page.goto(`/b/manage/events/${eventId}/guests`)
	await page.getByRole("radio", { name: /^Requests \(\d+\)$/ }).click()
	const row = page.getByRole("listitem").filter({ hasText: REQUESTER.email })
	await row.getByRole("button", { name: "Approve", exact: true }).click()
	await expect(page.getByText("Request approved").first()).toBeVisible()

	await guestPage.reload()
	await expect(guestPage.getByText("Add to calendar").first()).toBeVisible()
	await expect(guestPage.getByText("Request received")).toHaveCount(0)
	await guestContext.close()
})
