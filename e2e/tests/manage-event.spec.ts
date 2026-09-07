import { expect, test } from "@playwright/test"

import { callMethod, createDoc, deleteDoc, ensureTestTeam, getDoc } from "../helpers/frappe"

// Runs under the shared Administrator state, whose team hosts the event seeded by
// event.setup.ts — the one card guaranteed to carry a Manage button.
test.describe("Event workspace", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("/b/manage/events")
		await page.getByRole("link", { name: "Manage" }).first().click()
	})

	test("opens the event on its details section", async ({ page }) => {
		await expect(page).toHaveURL(/\/b\/manage\/events\/\d+\/details$/, { timeout: 15000 })
		// The details page opens on the event's own values, with the section after it
		// in the trail.
		await expect(page.getByRole("textbox", { name: "Event title" })).not.toHaveValue("", {
			timeout: 15000,
		})
		await expect(page.getByRole("banner").first()).toContainText("Details")
	})

	test("saves an edit, offering Save only once something changed", async ({ page }) => {
		const description = page.getByRole("textbox", { name: "Short description" })
		await expect(description).toBeVisible({ timeout: 15000 })

		const save = page.getByRole("button", { name: "Save" })
		await expect(save).toHaveCount(0)

		const text = `Edited at ${Date.now()}`
		await description.fill(text)
		await save.click()

		await expect(page.getByText("Event saved")).toBeVisible()
		await page.reload()
		await expect(description).toHaveValue(text, { timeout: 15000 })
	})

	test("shows the event's public address beside its name", async ({ page }) => {
		const field = page.getByRole("textbox", { name: "Event route" })
		await expect(field).toBeVisible({ timeout: 15000 })

		// The host is fixed text; only the part after the slash is editable.
		const route = await field.inputValue()
		expect(route).not.toBe("")

		const open = page.getByRole("link", { name: "Open event page" })
		await expect(open).toHaveAttribute("href", `/b/register/${route}`)
		await expect(open).toHaveAttribute("target", "_blank")
		await expect(page.getByRole("button", { name: "Copy" })).toBeVisible()
	})

	test("swaps the venue for a meeting link when the event turns virtual", async ({ page }) => {
		const venue = page.getByRole("combobox", { name: "Search venues, or add one" })
		await expect(venue).toBeVisible({ timeout: 15000 })

		await page.getByRole("button", { name: "Virtual" }).click()

		await expect(venue).toHaveCount(0)
		const link = page.getByRole("textbox", { name: "Meeting link" })
		await expect(link).toBeVisible()
		// Nothing to copy until a link is there.
		await expect(page.getByRole("button", { name: "Copy meeting link" })).toBeDisabled()

		await page.getByRole("button", { name: "In person" }).click()
		await expect(venue).toBeVisible()
	})

	test("swaps the sidebar for the event's own destinations", async ({ page }) => {
		for (const label of ["Details", "Guests", "Talks"]) {
			await expect(page.getByRole("link", { name: label })).toBeVisible({ timeout: 15000 })
		}
		await expect(page.getByRole("button", { name: "Back to events" })).toBeVisible()
		await expect(page.getByRole("link", { name: "My Tickets" })).toHaveCount(0)
	})

	test("moves between sections", async ({ page }) => {
		await page.getByRole("link", { name: "Talks" }).click()

		await expect(page).toHaveURL(/\/b\/manage\/events\/\d+\/talks$/)
		// Heading rather than text: the sidebar link is named Talks too.
		await expect(page.getByRole("heading", { name: "Talks", level: 2 })).toBeVisible({
			timeout: 15000,
		})
	})

	test("leaves the workspace through the back button", async ({ page }) => {
		await page.getByRole("button", { name: "Back to events" }).click()

		await expect(page).toHaveURL(/\/b\/manage\/events$/, { timeout: 15000 })
		await expect(page.getByRole("heading", { name: "Events", level: 1 })).toBeVisible()
	})
})

// The shared event has no venue, and a switch has to have one to lose, so this block
// seeds its own.
test.describe("Switching an event's medium", () => {
	let eventId: string

	test.beforeEach(async ({ page, request }) => {
		const team = await ensureTestTeam(request)
		// Event Venue is autonamed by prompt, so the docname is the venue's own name.
		const venue = `E2E Venue ${Date.now()}`
		await createDoc(request, "Event Venue", {
			__newname: venue,
			address: "1 Test Street",
			team,
		})
		const event = await callMethod<{ name: string }>(request, "buzz.api.events.create_event", {
			event: {
				team,
				title: `Medium Event ${Date.now()}`,
				start_date: "2030-01-01",
				start_time: "09:00:00",
				end_time: "17:00:00",
				venue,
			},
		})
		eventId = String(event.name)
		await page.goto(`/b/manage/events/${eventId}/details`)
	})

	test("drops the venue when the event turns virtual", async ({ page, request }) => {
		await expect(page.getByRole("combobox", { name: "Search venues, or add one" })).toBeVisible({
			timeout: 15000,
		})

		await page.getByRole("button", { name: "Virtual" }).click()
		await page.getByRole("button", { name: "Save" }).click()
		await expect(page.getByText("Event saved")).toBeVisible()

		// The calendar invite and the booking page read the venue whatever the medium is,
		// so it has to be gone from the record, not just from the form.
		const saved = await getDoc<{ medium: string; venue: string | null }>(
			request,
			"Buzz Event",
			eventId,
		)
		expect(saved.medium).toBe("Online")
		expect(saved.venue).toBeFalsy()
	})
})

// An event with no route yet has to claim one, so this block seeds its own rather than
// reusing the shared event, which already has one.
test.describe("Claiming a route", () => {
	let eventId: string

	test.beforeEach(async ({ page, request }) => {
		const team = await ensureTestTeam(request)
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
		})
		eventId = String(event.name)
		await page.goto(`/b/manage/events/${eventId}/details`)
	})

	test("reports whether a typed route is free", async ({ page }) => {
		const field = page.getByRole("textbox", { name: "Event route" })
		await expect(field).toBeVisible({ timeout: 15000 })

		await field.fill(`free-route-${Date.now()}`)
		await expect(page.getByText("This route is available.")).toBeVisible()

		// The shared event already answers to this one.
		await field.fill("test-event-e2e")
		await expect(page.getByText("This route is already taken.")).toBeVisible()

		// Reserved so an event cannot shadow /b/account.
		await field.fill("account")
		await expect(page.getByText("reserved")).toBeVisible()
	})
})

// Nothing seeds a ticket against the shared event, so a guest list read off it is empty
// in CI. This block seeds the guests it asserts on.
test.describe("Guest list", () => {
	const TICKET_TYPE = "Guest List Ticket"
	const ADD_ON = "Guest List T-Shirt"
	const GUESTS = [
		{ name: "Ada Lovelace", email: "ada@example.com" },
		{ name: "Grace Hopper", email: "grace@example.com" },
	]

	let eventId: string

	test.beforeEach(async ({ page, request }) => {
		const team = await ensureTestTeam(request)
		const event = await callMethod<{ name: string }>(request, "buzz.api.events.create_event", {
			event: {
				team,
				title: `Guest List Event ${Date.now()}`,
				start_date: "2030-01-01",
				start_time: "09:00:00",
				end_time: "17:00:00",
			},
		})
		eventId = String(event.name)

		const ticketType = await createDoc<{ name: string }>(request, "Event Ticket Type", {
			event: eventId,
			title: TICKET_TYPE,
			price: 0,
			currency: "INR",
			is_published: 1,
		})
		const addOn = await createDoc<{ name: string }>(request, "Ticket Add-on", {
			event: eventId,
			title: ADD_ON,
			user_selects_option: 1,
			options: ["Small", "Large"].join("\n"),
			price: 0,
			currency: "INR",
		})

		for (const [index, guest] of GUESTS.entries()) {
			const ticket = await createDoc(request, "Event Ticket", {
				event: eventId,
				ticket_type: ticketType.name,
				attendee_name: guest.name,
				attendee_email: guest.email,
				// Only the first guest holds one, so the badges belong to a row rather than
				// to every row alike.
				add_ons:
					index === 0 ? [{ add_on: addOn.name, value: "Large", price: 0, currency: "INR" }] : [],
			})
			// A draft ticket belongs to a booking still being paid for; only a submitted
			// one is somebody coming.
			await callMethod(request, "frappe.client.submit", { doc: ticket })
		}

		await page.goto(`/b/manage/events/${eventId}/details`)
	})

	test("lists the event's guests", async ({ page }) => {
		await page.getByRole("link", { name: "Guests" }).click()

		await expect(page).toHaveURL(new RegExp(`/b/manage/events/${eventId}/guests$`))
		await expect(page.getByRole("heading", { name: "Guest list" })).toBeVisible()
		const rows = page.getByRole("list").getByRole("listitem")
		await expect(rows).toHaveCount(GUESTS.length, { timeout: 15000 })

		// The count is the number of rows under it, not a separate claim.
		const registrations = Number(await page.getByText(/^\d+$/).first().textContent())
		expect(registrations).toBe(GUESTS.length)
		// The registration state is the actions rail's own control, which reads the state
		// out and is how it gets changed.
		await expect(page.getByRole("button", { name: /Registration (Open|Closed)/ })).toBeVisible()

		// Newest registration first, which is the reverse of the seeding above — so each
		// row is found by its guest rather than by a position the sort order decides. Both
		// the ticket type and the add-on are autonamed, so a docname here would read as a
		// bare number.
		const withAddOn = rows.filter({ hasText: GUESTS[0].email })
		await expect(withAddOn).toContainText(TICKET_TYPE)
		await expect(withAddOn).toContainText(ADD_ON)
		await expect(rows.filter({ hasText: GUESTS[1].email })).not.toContainText(ADD_ON)
	})

	test("narrows the guest list by search", async ({ page }) => {
		await page.goto(`/b/manage/events/${eventId}/guests`)

		const rows = page.getByRole("list").getByRole("listitem")
		await expect(rows).toHaveCount(GUESTS.length, { timeout: 15000 })

		const search = page.getByRole("textbox", { name: "Search by name or email" })
		await search.fill(GUESTS[1].email)
		await expect(rows).toHaveCount(1)
		await expect(rows.first()).toContainText(GUESTS[1].email)

		// By name as well as by email.
		await search.fill("Ada")
		await expect(rows).toHaveCount(1)
		await expect(rows.first()).toContainText(GUESTS[0].email)

		await search.fill("")
		await expect(rows).toHaveCount(GUESTS.length)
	})
})

// The details form holds edits in memory, so moving between sections used to drop them.
// They are kept in localStorage now; this block seeds its own event rather than leaving
// the shared one dirty for the specs above.
test.describe("Unsaved details", () => {
	let eventId: string

	test.beforeEach(async ({ page, request }) => {
		const team = await ensureTestTeam(request)
		const event = await callMethod<{ name: string }>(request, "buzz.api.events.create_event", {
			event: {
				team,
				title: `Draft Event ${Date.now()}`,
				start_date: "2030-01-01",
				start_time: "09:00:00",
				end_time: "17:00:00",
			},
		})
		eventId = String(event.name)
		await page.goto(`/b/manage/events/${eventId}/details`)
	})

	// Each run seeds its own event, so each run takes it away again rather than leaving a
	// trail of them on the shared site.
	test.afterEach(async ({ request }) => {
		await deleteDoc(request, "Buzz Event", eventId).catch(() => {})
	})

	test("keeps edits through a trip to another section, and drops them on discard", async ({
		page,
	}) => {
		const description = page.getByRole("textbox", { name: "Short description" })
		await expect(description).toBeVisible({ timeout: 15000 })

		const text = `Typed but not saved ${Date.now()}`
		await description.fill(text)
		// Save showing is the form registering the edit, so the trip below starts dirty.
		await expect(page.getByRole("button", { name: "Save" })).toBeVisible()

		await page.getByRole("link", { name: "Guests" }).click()
		await expect(page).toHaveURL(new RegExp(`/b/manage/events/${eventId}/guests$`))
		await page.getByRole("link", { name: "Details" }).click()

		await expect(description).toHaveValue(text, { timeout: 15000 })
		await expect(page.getByText("Restored your unsaved changes")).toBeVisible()
		await expect(page.getByRole("button", { name: "Save" })).toBeVisible()

		// Discard is the deliberate way out, and it has to take the stored draft with it.
		await page.getByRole("button", { name: "Discard" }).click()
		await expect(description).toHaveValue("")

		await page.getByRole("link", { name: "Guests" }).click()
		await expect(page).toHaveURL(new RegExp(`/b/manage/events/${eventId}/guests$`))
		await page.getByRole("link", { name: "Details" }).click()

		await expect(description).toHaveValue("", { timeout: 15000 })
		await expect(page.getByRole("button", { name: "Save" })).toHaveCount(0)
	})

	// Leaving the site warns first, and taking that exit means the edits go with it —
	// otherwise the reload would hand back the text the warning offered to save.
	test("warns on reload, and drops the draft once the warning is accepted", async ({ page }) => {
		const description = page.getByRole("textbox", { name: "Short description" })
		await expect(description).toBeVisible({ timeout: 15000 })

		await description.fill(`Typed then reloaded ${Date.now()}`)
		await expect(page.getByRole("button", { name: "Save" })).toBeVisible()

		let warned = false
		page.on("dialog", (dialog) => {
			warned = dialog.type() === "beforeunload"
			return dialog.accept()
		})
		await page.reload()

		expect(warned).toBe(true)
		await expect(description).toHaveValue("", { timeout: 15000 })
		await expect(page.getByRole("button", { name: "Save" })).toHaveCount(0)
		await expect(page.getByText("Restored your unsaved changes")).toHaveCount(0)
	})

	test("drops the draft once the edits are saved", async ({ page }) => {
		const description = page.getByRole("textbox", { name: "Short description" })
		await expect(description).toBeVisible({ timeout: 15000 })

		const text = `Saved after a detour ${Date.now()}`
		await description.fill(text)
		await page.getByRole("button", { name: "Save" }).click()
		await expect(page.getByText("Event saved")).toBeVisible()

		await page.getByRole("link", { name: "Guests" }).click()
		await expect(page).toHaveURL(new RegExp(`/b/manage/events/${eventId}/guests$`))
		await page.getByRole("link", { name: "Details" }).click()

		// The value is the event's own now, so it arrives without a draft behind it.
		await expect(description).toHaveValue(text, { timeout: 15000 })
		await expect(page.getByText("Restored your unsaved changes")).toHaveCount(0)
		await expect(page.getByRole("button", { name: "Save" })).toHaveCount(0)
	})
})
