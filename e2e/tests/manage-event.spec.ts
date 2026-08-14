import { expect, test } from "@playwright/test";
import { callMethod, ensureTestTeam } from "../helpers/frappe";

// Runs under the shared Administrator state, whose team hosts the event seeded by
// event.setup.ts — the one card guaranteed to carry a Manage button.
test.describe("Event workspace", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("/b/manage/events");
		await page.getByRole("link", { name: "Manage" }).first().click();
	});

	test("opens the event on its details section", async ({ page }) => {
		await expect(page).toHaveURL(/\/b\/manage\/events\/\d+\/details$/, { timeout: 15000 });
		// The details page opens on the event's own values, with the section after it
		// in the trail.
		await expect(page.getByRole("textbox", { name: "Event title" })).not.toHaveValue("", {
			timeout: 15000,
		});
		await expect(page.getByRole("banner").first()).toContainText("Details");
	});

	test("saves an edit, offering Save only once something changed", async ({ page }) => {
		const description = page.getByRole("textbox", { name: "Short description" });
		await expect(description).toBeVisible({ timeout: 15000 });

		const save = page.getByRole("button", { name: "Save" });
		await expect(save).toHaveCount(0);

		const text = `Edited at ${Date.now()}`;
		await description.fill(text);
		await save.click();

		await expect(page.getByText("Event saved")).toBeVisible();
		await page.reload();
		await expect(description).toHaveValue(text, { timeout: 15000 });
	});

	test("shows the event's public address beside its name", async ({ page }) => {
		const field = page.getByRole("textbox", { name: "Event route" });
		await expect(field).toBeVisible({ timeout: 15000 });

		// The host is fixed text; only the part after the slash is editable.
		const route = await field.inputValue();
		expect(route).not.toBe("");

		const open = page.getByRole("link", { name: "Open event page" });
		await expect(open).toHaveAttribute("href", `/b/register/${route}`);
		await expect(open).toHaveAttribute("target", "_blank");
		await expect(page.getByRole("button", { name: "Copy" })).toBeVisible();
	});

	test("swaps the venue for a meeting link when the event turns virtual", async ({ page }) => {
		const venue = page.getByRole("combobox", { name: "Search venues, or add one" });
		await expect(venue).toBeVisible({ timeout: 15000 });

		await page.getByRole("button", { name: "Virtual" }).click();

		await expect(venue).toHaveCount(0);
		const link = page.getByRole("textbox", { name: "Meeting link" });
		await expect(link).toBeVisible();
		// Nothing to copy until a link is there.
		await expect(page.getByRole("button", { name: "Copy meeting link" })).toBeDisabled();

		await page.getByRole("button", { name: "In person" }).click();
		await expect(venue).toBeVisible();
	});

	test("swaps the sidebar for the event's own destinations", async ({ page }) => {
		for (const label of ["Back", "Details", "Guests", "Talks"]) {
			await expect(page.getByRole("link", { name: label })).toBeVisible({ timeout: 15000 });
		}
		await expect(page.getByRole("link", { name: "My Tickets" })).toHaveCount(0);
	});

	test("lists the event's guests", async ({ page }) => {
		await page.getByRole("link", { name: "Guests" }).click();

		await expect(page).toHaveURL(/\/b\/manage\/events\/\d+\/guests$/);
		await expect(page.getByRole("heading", { name: "Event guests", level: 1 })).toBeVisible();
		// The shared event is the one tickets.setup.ts books against, so it has guests,
		// and each row is a name rather than a blank.
		const names = page.getByRole("list").getByRole("listitem");
		await expect(names.first()).toBeVisible({ timeout: 15000 });
		await expect(names.first()).not.toBeEmpty();
	});

	test("moves between sections", async ({ page }) => {
		await page.getByRole("link", { name: "Talks" }).click();

		await expect(page).toHaveURL(/\/b\/manage\/events\/\d+\/talks$/);
		await expect(page.getByText("Work in progress")).toBeVisible();
	});

	test("leaves the workspace through the back item", async ({ page }) => {
		await page.getByRole("link", { name: "Back" }).click();

		await expect(page).toHaveURL(/\/b\/manage\/events$/, { timeout: 15000 });
		await expect(page.getByRole("heading", { name: "Events", level: 1 })).toBeVisible();
	});
});

// An event with no route yet has to claim one, so this block seeds its own rather than
// reusing the shared event, which already has one.
test.describe("Claiming a route", () => {
	let eventId: string;

	test.beforeEach(async ({ page, request }) => {
		const team = await ensureTestTeam(request);
		// Through the app's own endpoint: it fills the category and host that a bare
		// insert would be missing.
		const event = await callMethod<{ name: string }>(request, "buzz.api.events.create_event", {
			event: {
				team,
				title: `Routeless Event ${Date.now()}`,
				start_date: "2030-01-01",
				start_time: "09:00:00",
				end_time: "17:00:00",
			},
		});
		eventId = String(event.name);
		await page.goto(`/b/manage/events/${eventId}/details`);
	});

	test("reports whether a typed route is free", async ({ page }) => {
		const field = page.getByRole("textbox", { name: "Event route" });
		await expect(field).toBeVisible({ timeout: 15000 });

		await field.fill(`free-route-${Date.now()}`);
		await expect(page.getByText("This route is available.")).toBeVisible();

		// The shared event already answers to this one.
		await field.fill("test-event-e2e");
		await expect(page.getByText("This route is already taken.")).toBeVisible();

		// Reserved so an event cannot shadow /b/account.
		await field.fill("account");
		await expect(page.getByText("reserved")).toBeVisible();
	});
});

// A team's own events are all manageable, so those cards drop the button and become
// the link themselves.
test.describe("Team events card", () => {
	test("opens the workspace on click, with no Manage button of its own", async ({ page }) => {
		await page.goto("/b/manage/events");
		await page.getByRole("link", { name: "Events", exact: true }).click();
		await expect(page).toHaveURL(/\/b\/manage\/team\/events$/, { timeout: 15000 });

		// Keyed on the href, not a title: which events the team owns varies by site.
		const card = page.locator('a[href^="/b/manage/events/"]').first();
		await expect(card).toBeVisible({ timeout: 15000 });
		await expect(page.getByRole("link", { name: "Manage" })).toHaveCount(0);
		await card.click();

		await expect(page).toHaveURL(/\/b\/manage\/events\/\d+\/details$/);
	});
});
