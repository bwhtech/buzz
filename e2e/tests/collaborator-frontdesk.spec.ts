import {
	APIRequestContext,
	expect,
	Page,
	request as playwrightRequest,
	test,
} from "@playwright/test"

import {
	callMethod,
	createDoc,
	createUserWithRoles,
	ensureEventHost,
	ensureTestTeam,
	getList,
	loginViaAPI,
	newApiContext,
	openRegistrations,
} from "../helpers"
import { CheckInPage } from "../pages"

interface NamedDoc {
	name: string
}

const COLLABORATOR_EMAIL = "guests-collaborator-e2e@buzz.test"
const COLLABORATOR_PASSWORD = "Collaborator@123"
const ATTENDEE_NAME = "Collaborator Guest"

const url = (method: string) => `/api/v2/method/buzz.api.checkin.${method}`

let admin: APIRequestContext
let eventName: string
let ticketType: string

async function createTicket(): Promise<string> {
	const ticket = await createDoc<NamedDoc & Record<string, unknown>>(admin, "Event Ticket", {
		event: eventName,
		ticket_type: ticketType,
		attendee_name: ATTENDEE_NAME,
		attendee_email: "collaborator-guest@buzz.test",
	})
	if (ticket.docstatus === 0) {
		await callMethod(admin, "frappe.client.submit", { doc: ticket })
	}
	return ticket.name
}

async function seedEvent(): Promise<void> {
	const team = await ensureTestTeam(admin)
	const host = await ensureEventHost(admin, "E2E Collaborator Host", team)
	const startDate = new Date()
	startDate.setDate(startDate.getDate() + 7)
	const event = await createDoc<NamedDoc>(admin, "Buzz Event", {
		team,
		title: `E2E Collaborator Check-in ${Date.now()}`,
		category: "E2E Test Category",
		host,
		route: `collaborator-check-in-${Date.now()}`,
		start_date: startDate.toISOString().split("T")[0],
		end_date: startDate.toISOString().split("T")[0],
		start_time: "09:00:00",
		end_time: "17:00:00",
		medium: "In Person",
		is_published: 1,
	})
	eventName = String(event.name)
	await openRegistrations(admin, eventName)
	const type = await createDoc<NamedDoc>(admin, "Event Ticket Type", {
		event: eventName,
		title: "Collaborator Ticket",
		is_published: 1,
	})
	ticketType = type.name
}

async function seedCollaborator(): Promise<void> {
	await createUserWithRoles(admin, {
		email: COLLABORATOR_EMAIL,
		firstName: "Guests Collaborator",
		password: COLLABORATOR_PASSWORD,
		roles: ["Buzz User"],
	})
	await createDoc(admin, "Buzz Event Collaborator", {
		event: eventName,
		email: COLLABORATOR_EMAIL,
		user: COLLABORATOR_EMAIL,
		status: "Accepted",
		details_access: "View",
		guests_access: "Edit",
	})
}

test.beforeAll(async ({ baseURL }) => {
	admin = await newApiContext(baseURL!)
	await seedEvent()
	await seedCollaborator()
})

test.afterAll(async () => {
	await admin?.dispose()
})

// Collects the API calls that failed, so a stray 403 (such as NotTeamMember) fails the test.
function trackApiFailures(page: Page): string[] {
	const failures: string[] = []
	page.on("response", async (response) => {
		if (response.status() >= 400 && response.url().includes("/api/")) {
			failures.push(`${response.status()} ${response.url()} ${await response.text()}`)
		}
	})
	return failures
}

test.describe("Collaborator with guests Edit access", () => {
	test.use({ storageState: { cookies: [], origins: [] } })

	test("checks a guest in through the API", async ({ baseURL }) => {
		const ticketId = await createTicket()
		const collaborator = await playwrightRequest.newContext({ baseURL })
		await loginViaAPI(collaborator, COLLABORATOR_EMAIL, COLLABORATOR_PASSWORD)

		const events = await collaborator.get(url("get_checkin_events"))
		expect((await events.json()).data.map((event) => event.name)).toContain(eventName)
		const validation = await collaborator.get(url("validate_ticket_for_checkin"), {
			params: { ticket_id: ticketId },
		})
		expect(validation.status()).toBe(200)
		const checkIn = await collaborator.post(url("checkin_ticket"), {
			data: { ticket_id: ticketId },
		})
		expect(checkIn.status()).toBe(200)
		await collaborator.dispose()
	})

	test("checks a guest in through the scanner", async ({ page }) => {
		const ticketId = await createTicket()
		const failures = trackApiFailures(page)
		await loginViaAPI(page.request, COLLABORATOR_EMAIL, COLLABORATOR_PASSWORD)

		const checkInPage = new CheckInPage(page)
		await checkInPage.goto(eventName)
		await checkInPage.expectScannerVisible()
		await checkInPage.submitTicketId(ticketId)
		await checkInPage.expectTicketModal(ATTENDEE_NAME)
		await checkInPage.confirmCheckIn()

		const checkIns = await getList<NamedDoc>(admin, "Event Check In", {
			filters: { ticket: ["=", ticketId] },
		})
		expect(checkIns.length).toBe(1)
		expect(failures).toEqual([])
	})

	test("checks a guest in from the guest list and opens the event guests page", async ({
		page,
	}) => {
		await createTicket()
		const failures = trackApiFailures(page)
		await loginViaAPI(page.request, COLLABORATOR_EMAIL, COLLABORATOR_PASSWORD)

		await page.goto(`/b/check-in/${eventName}`)
		const checkIn = page.getByRole("button", { name: /^Check in/ }).first()
		const recorded = page.waitForResponse((response) => response.url().includes("checkin_ticket"))
		await checkIn.click()
		expect((await recorded).status()).toBe(200)

		await page.getByRole("link", { name: "Event dashboard" }).click()
		await page.waitForURL(/guests/)
		await page.waitForLoadState("networkidle")
		await expect(page.getByText(ATTENDEE_NAME).first()).toBeVisible()
		expect(failures).toEqual([])
	})
})
