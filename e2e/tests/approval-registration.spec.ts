import { type Browser, type Page, expect, test } from "@playwright/test"

import {
	APPROVAL_EVENT_ROUTE,
	APPROVAL_TICKET_TITLE,
	REQUESTERS,
} from "../data/approval-registration"
import { newApiContext } from "../helpers/auth"
import { callMethod, getList } from "../helpers/frappe"
import { BookingPage } from "../pages"

type Requester = (typeof REQUESTERS)[keyof typeof REQUESTERS]

let eventId: string

test.beforeAll(async ({ baseURL }) => {
	const api = await newApiContext(baseURL!)
	const [event] = await getList<{ name: string }>(api, "Buzz Event", {
		filters: { route: APPROVAL_EVENT_ROUTE },
		limit: 1,
	})
	eventId = event.name
	await api.dispose()
})

async function bookingOf(baseURL: string, requester: Requester) {
	const api = await newApiContext(baseURL)
	const [booking] = await getList<{ name: string; docstatus: number; status: string }>(
		api,
		"Event Booking",
		{
			fields: ["name", "docstatus", "status"],
			filters: { event: eventId, user: requester.email },
			orderBy: "creation desc",
			limit: 1,
		},
	)
	await api.dispose()
	return booking
}

// A retried test would otherwise hit the one-pending-request-per-guest rule.
async function declineEarlierRequest(baseURL: string, requester: Requester) {
	const earlier = await bookingOf(baseURL, requester)
	if (earlier?.status !== "Approval Pending") return
	const api = await newApiContext(baseURL)
	await callMethod(api, "buzz.api.booking.approvals.decline_bookings", {
		event: eventId,
		bookings: [earlier.name],
	})
	await api.dispose()
}

// The requester signs in on a context of their own, so the organizer keeps the shared session.
async function requestToJoin(browser: Browser, requester: Requester, baseURL: string) {
	await declineEarlierRequest(baseURL, requester)
	const context = await browser.newContext({ storageState: requester.statePath })
	const page = await context.newPage()
	const bookingPage = new BookingPage(page)

	await bookingPage.goto(APPROVAL_EVENT_ROUTE)
	await bookingPage.waitForFormLoad()
	await expect(page.getByText("Requires approval").first()).toBeVisible()
	await bookingPage.goToAttendees()
	await bookingPage.fillMyDetails(requester.name, "E2E", requester.email)
	await bookingPage.submit()

	await expect(page).toHaveURL(/\/booking-success\/.+/)
	await expect(page.getByText("Pending approval").first()).toBeVisible({ timeout: 30000 })
	return { page, context }
}

function pendingRow(page: Page, requester: Requester) {
	return page
		.getByRole("listitem")
		.filter({ hasText: requester.email })
		.filter({ has: page.getByRole("button", { name: "Approve" }) })
}

async function openPendingList(page: Page) {
	await page.goto(`/b/manage/events/${eventId}/guests?view=pending`)
	await expect(page.getByRole("radio", { name: /^Pending \(\d+\)$/ })).toBeVisible()
}

async function openTicketTypeDrawer(page: Page) {
	await page.goto(`/b/manage/events/${eventId}/registrations`)
	await page.getByText(APPROVAL_TICKET_TITLE).first().click()
	return page.getByRole("switch", { name: "Requires approval" })
}

// Sets the switch rather than toggling it, so a retried test starts from the state it expects.
async function setApproval(page: Page, enabled: boolean) {
	const approval = await openTicketTypeDrawer(page)
	await expect(approval).toBeVisible()
	if ((await approval.isChecked()) !== enabled) await approval.click()
	return approval
}

test.describe.configure({ mode: "serial" })

test.describe("Approval-required registration", () => {
	test("organizer turns approval on, approves a request, and the booking is confirmed", async ({
		page,
		browser,
		baseURL,
	}) => {
		await expect(await setApproval(page, true)).toBeChecked()

		const requester = REQUESTERS.approved
		const { page: guestPage, context } = await requestToJoin(browser, requester, baseURL!)

		await openPendingList(page)
		await pendingRow(page, requester).getByRole("button", { name: "Approve" }).click()
		await expect(pendingRow(page, requester)).toHaveCount(0)

		await guestPage.reload()
		await expect(guestPage.getByText("Add to calendar").first()).toBeVisible()
		await expect(guestPage.getByText("Pending approval")).toHaveCount(0)
		const booking = await bookingOf(baseURL!, requester)
		expect(booking.docstatus).toBe(1)
		await context.close()
	})

	test("a declined request shows as declined to the guest", async ({ page, browser, baseURL }) => {
		const requester = REQUESTERS.declined
		const { page: guestPage, context } = await requestToJoin(browser, requester, baseURL!)

		await openPendingList(page)
		await pendingRow(page, requester).getByRole("button", { name: "Decline" }).click()
		await page.getByLabel("Message (optional)").fill("The event is full of speakers")
		await page.getByRole("dialog").getByRole("button", { name: "Decline" }).click()
		await expect(page.getByRole("dialog")).toHaveCount(0)
		await expect(pendingRow(page, requester)).toHaveCount(0)

		await guestPage.reload()
		await expect(guestPage.getByText("Request declined").first()).toBeVisible()
		await expect(guestPage.getByText("The event is full of speakers")).toBeVisible()
		await context.close()
	})

	test("turning approval off keeps waiting requests pending", async ({
		page,
		browser,
		baseURL,
	}) => {
		const requester = REQUESTERS.kept
		await setApproval(page, true)
		const earlier = await bookingOf(baseURL!, requester)
		if (earlier?.status !== "Approval Pending") {
			const { context } = await requestToJoin(browser, requester, baseURL!)
			await context.close()
		}

		await setApproval(page, false)

		const dialog = page.getByRole("dialog")
		await expect(dialog.getByText("1 request is still waiting").first()).toBeVisible()
		await expect(dialog.getByText("Keep them pending").first()).toBeVisible()
		await dialog.getByRole("button", { name: "Confirm" }).click()
		await expect(dialog).toHaveCount(0)

		const booking = await bookingOf(baseURL!, requester)
		expect(booking.docstatus).toBe(0)
		expect(booking.status).toBe("Approval Pending")

		await page.goto(`/b/manage/events/${eventId}/guests?view=pending`)
		await expect(pendingRow(page, requester)).toBeVisible()
	})
})
