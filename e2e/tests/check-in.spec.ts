import { APIRequestContext, expect, test } from "@playwright/test";
import { getList, newApiContext } from "../helpers";
import { CheckInPage } from "../pages";
import {
	CHECK_IN_ATTENDEE_EMAIL,
	CHECK_IN_ATTENDEE_NAME,
	CHECK_IN_EVENT_ROUTE,
	NO_ROLE_STATE_PATH,
} from "../data/check-in";

interface NamedDoc {
	name: string;
}

let admin: APIRequestContext;
let eventName: string;
let ticketId: string;

test.beforeAll(async ({ baseURL }) => {
	admin = await newApiContext(baseURL!);

	const events = await getList<NamedDoc>(admin, "Buzz Event", {
		filters: { route: ["=", CHECK_IN_EVENT_ROUTE] },
	});
	expect(events.length).toBeGreaterThan(0);
	eventName = events[0].name;

	const tickets = await getList<NamedDoc>(admin, "Event Ticket", {
		filters: { attendee_email: ["=", CHECK_IN_ATTENDEE_EMAIL] },
	});
	expect(tickets.length).toBeGreaterThan(0);
	ticketId = tickets[0].name;
});

test.afterAll(async () => {
	await admin?.dispose();
});

test.describe("Check-in scanner", () => {
	test("front-desk user reaches the scanner", async ({ page }) => {
		const checkInPage = new CheckInPage(page);
		await checkInPage.goto(eventName);

		await checkInPage.expectScannerVisible();
	});

	test("a valid ticket opens the details modal", async ({ page }) => {
		const checkInPage = new CheckInPage(page);
		await checkInPage.goto(eventName);
		await checkInPage.expectScannerVisible();

		await checkInPage.submitTicketId(ticketId);

		await checkInPage.expectTicketModal(CHECK_IN_ATTENDEE_NAME);
	});

	test("an unknown ticket surfaces the server message", async ({ page }) => {
		const checkInPage = new CheckInPage(page);
		await checkInPage.goto(eventName);
		await checkInPage.expectScannerVisible();

		await checkInPage.submitTicketId("NOSUCHTICKET");

		await checkInPage.expectToast(/No ticket matches this code/i);
	});

	// Ordered last: it consumes the seeded ticket for the day.
	test("checking in records the visit, and a second scan is refused", async ({ page }) => {
		const checkInPage = new CheckInPage(page);
		await checkInPage.goto(eventName);
		await checkInPage.expectScannerVisible();

		await checkInPage.submitTicketId(ticketId);
		await checkInPage.expectTicketModal(CHECK_IN_ATTENDEE_NAME);
		await checkInPage.confirmCheckIn();

		await expect(checkInPage.lastScanResult).toBeVisible({ timeout: 15000 });
		const checkIns = await getList<NamedDoc>(admin, "Event Check In", {
			filters: { ticket: ["=", ticketId] },
		});
		expect(checkIns.length).toBe(1);

		await checkInPage.submitTicketId(ticketId);
		await checkInPage.expectToast(/already checked in today/i);
	});
});

test.describe("Check-in access control", () => {
	test.use({ storageState: NO_ROLE_STATE_PATH });

	test("a user without the Frontdesk Manager role is refused", async ({ page }) => {
		const checkInPage = new CheckInPage(page);
		await checkInPage.goto();

		await checkInPage.expectAccessDenied();
	});
});
