import { expect, test } from "@playwright/test"

import { PAID_EVENT_ROUTE, REQUESTER, REQUESTS_EVENT_ROUTE } from "../data/registration-requests"
import { newApiContext } from "../helpers/auth"
import { getList } from "../helpers/frappe"
import { BookingPage } from "../pages"

async function findEvent(baseURL: string, route = REQUESTS_EVENT_ROUTE) {
	const api = await newApiContext(baseURL)
	const [event] = await getList<{ name: string }>(api, "Buzz Event", {
		filters: { route },
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

test("approving a paid request offers Pay now, which leads to payment", async ({
	page,
	browser,
	baseURL,
}) => {
	const eventId = await findEvent(baseURL!, PAID_EVENT_ROUTE)

	const guestContext = await browser.newContext({ storageState: REQUESTER.statePath })
	const guestPage = await guestContext.newPage()
	const bookingPage = new BookingPage(guestPage)

	await bookingPage.goto(PAID_EVENT_ROUTE)
	await bookingPage.waitForFormLoad()
	await bookingPage.goToAttendees()
	await bookingPage.fillMyDetails(REQUESTER.name, "Paid", REQUESTER.email)
	await bookingPage.continue()
	await expect(guestPage.getByRole("button", { name: "Request to join" })).toBeVisible()
	await bookingPage.submit()
	await expect(guestPage).toHaveURL(/\/booking-success\/.+/)
	const booking = new URL(guestPage.url()).pathname.split("/").pop()

	await page.goto(`/b/manage/events/${eventId}/approvals`)
	await page.getByRole("button", { name: `Open ${REQUESTER.name} Paid` }).click()
	await page.getByRole("button", { name: "Approve & send link" }).click()
	await expect(page.getByText(/^Approved /).first()).toBeVisible()

	const drawer = guestPage.getByRole("dialog")
	await expect(async () => {
		await guestPage.goto(`/b/manage/events?booking=${booking}`)
		await expect(drawer.getByRole("button", { name: "Pay now" })).toBeVisible({ timeout: 8000 })
	}).toPass({ timeout: 40000 })
	await expect(drawer.getByText("You're approved")).toBeVisible()

	// The gateway is stubbed: the test asserts the request and the redirect, not a live checkout.
	const checkoutPath = "/b/checkout-stub"
	await guestPage.route(/get_request_payment_link/, (route) =>
		route.fulfill({ json: { data: { payment_link: checkoutPath } } }),
	)
	const paymentRequest = guestPage.waitForRequest(/get_request_payment_link/)
	await drawer.getByRole("button", { name: "Pay now" }).click()
	expect((await paymentRequest).postDataJSON()).toMatchObject({ booking })
	await expect(guestPage).toHaveURL(new RegExp(`${checkoutPath}$`))
	await guestContext.close()
})
