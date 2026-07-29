import { expect, test } from "@playwright/test";
import { ADD_ON_TITLE, ATTENDEE_STATE_PATH, TICKETS_EVENT_TITLE } from "../data/tickets";
import { newApiContext } from "../helpers/auth";
import { getList } from "../helpers/frappe";

interface NamedDoc {
	name: string;
}

interface TicketDetails {
	can_transfer_ticket: unknown;
	can_change_add_ons: unknown;
	can_request_cancellation: unknown;
	add_ons: Array<{ title: string; value: string; options: string[] }>;
}

// The attendee owns the ticket; get_ticket_details refuses everyone else.
test.use({ storageState: ATTENDEE_STATE_PATH });

async function seededTicketId(baseURL: string): Promise<string> {
	// The attendee cannot list Event Ticket over REST, so look the id up as Administrator.
	const admin = await newApiContext(baseURL);
	try {
		const events = await getList<NamedDoc>(admin, "Buzz Event", {
			filters: { title: ["=", TICKETS_EVENT_TITLE] },
		});
		expect(events.length).toBeGreaterThan(0);

		const tickets = await getList<NamedDoc>(admin, "Event Ticket", {
			filters: { event: ["=", events[0].name] },
		});
		expect(tickets.length).toBeGreaterThan(0);
		return tickets[0].name;
	} finally {
		await admin.dispose();
	}
}

/** The details payload the page itself fetched — no second request, no CSRF juggling. */
async function loadTicketDetails(page, ticketId: string): Promise<TicketDetails> {
	const pending = page.waitForResponse(
		(response) => response.url().includes("get_ticket_details"),
		{ timeout: 20000 },
	);
	await page.goto(`/b/tickets/${ticketId}`);
	const body = await (await pending).json();
	return body.message as TicketDetails;
}

test.describe("Ticket Details", () => {
	test("shows the ticket to its attendee", async ({ page, baseURL }) => {
		const ticketId = await seededTicketId(baseURL!);

		await page.goto(`/b/tickets/${ticketId}`);
		await expect(page.getByText("Ticket Details")).toBeVisible({ timeout: 15000 });
		await expect(page.getByText("Tickets Attendee").first()).toBeVisible();
		await expect(page.getByText(ADD_ON_TITLE)).toBeVisible();
	});

	test("reports the action windows as plain booleans", async ({ page, baseURL }) => {
		const details = await loadTicketDetails(page, await seededTicketId(baseURL!));

		// The event is seeded 60 days out, so every window is open. These used to arrive as
		// {can_transfer: true, event_id: ...} wrappers.
		expect(details.can_transfer_ticket).toBe(true);
		expect(details.can_change_add_ons).toBe(true);
		expect(details.can_request_cancellation).toBe(true);
	});

	test("carries the add-on with its selectable options", async ({ page, baseURL }) => {
		const details = await loadTicketDetails(page, await seededTicketId(baseURL!));

		expect(details.add_ons).toHaveLength(1);
		expect(details.add_ons[0].title).toBe(ADD_ON_TITLE);
		expect(details.add_ons[0].value).toBe("Veg");
		expect(details.add_ons[0].options).toEqual(["Veg", "Non-veg"]);
	});
});
