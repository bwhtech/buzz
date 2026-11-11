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
	await bookingPage.continue()
	await expect(guestPage.getByRole("button", { name: "Request to join" })).toBeVisible()
	await bookingPage.submit()

	await expect(guestPage).toHaveURL(/\/booking-success\/.+/)
	await expect(guestPage.getByText("Request received").first()).toBeVisible({ timeout: 30000 })
	const successUrl = guestPage.url()

	// The request holds no ticket, yet its event is in the guest's feed with the same notice.
	const booking = new URL(successUrl).pathname.split("/").pop()
	await guestPage.goto(`/b/manage/events?booking=${booking}`)
	await expect(guestPage.getByRole("dialog").getByText("Request received")).toBeVisible({
		timeout: 15000,
	})
	await guestPage.goto(successUrl)

	// The registration page counts the request and shows the mode the ticket type flag implies.
	await page.goto(`/b/manage/events/${eventId}/registrations`)
	await expect(page.getByRole("link", { name: /Waiting for review/ })).toContainText("1")
	await expect(page.getByRole("radio", { name: /Review some tickets/ })).toBeChecked()

	await page.getByRole("link", { name: /Waiting for review/ }).click()
	await expect(page).toHaveURL(/\/approvals$/)
	await page.getByRole("button", { name: `Open ${REQUESTER.name} E2E` }).click()
	await page.getByRole("button", { name: "Approve", exact: true }).click()
	await expect(page.getByText(/^Approved /).first()).toBeVisible()

	// The write is held for the Undo window, so the guest's booking confirms a few seconds later.
	await expect(async () => {
		await guestPage.reload()
		await expect(guestPage.getByText("Add to calendar").first()).toBeVisible({ timeout: 2000 })
	}).toPass({ timeout: 20000 })
	await expect(guestPage.getByText("Request received")).toHaveCount(0)
	await guestContext.close()
})
