import assert from "node:assert/strict"
import { test } from "node:test"

import { discoverEvents, firstEventPath, managerNavigation } from "./managerNavigation.ts"

const labels = (items: { label: string }[]) => items.map((item) => item.label)

test("the root offers events, proposals and teams", () => {
	const items = managerNavigation({ creatingEvent: false, hasSponsorships: false })
	assert.deepEqual(labels(items), ["Events", "Talk Proposals", "Communities"])
	assert.equal(items.at(-1)?.startsGroup, true)
})

test("sponsorship appears once the user has an inquiry", () => {
	const items = managerNavigation({ creatingEvent: false, hasSponsorships: true })
	assert.deepEqual(labels(items), ["Events", "Talk Proposals", "Sponsorship", "Communities"])
})

test("an event offers its own sections, scoped to its id", () => {
	const items = managerNavigation({ eventId: "EV-1", creatingEvent: false, hasSponsorships: true })
	assert.deepEqual(labels(items), [
		"Overview",
		"Details",
		"Tickets",
		"Payments",
		"Transactions",
		"Coupons",
		"Guests",
		"Approvals",
		"Waitlist",
		"Check-in",
		"Talks",
		"Schedule",
		"Announcements",
		"Sponsorships",
		"Settings",
	])
	assert.ok(items.every((item) => item.to.startsWith("/manage/events/EV-1/")))
})

test("approvals and waitlist carry their counts, and only pending approvals get a dot", () => {
	const items = managerNavigation({
		eventId: "EV-1",
		creatingEvent: false,
		hasSponsorships: false,
		requestCounts: { pending: 3, waiting: 5 },
	})
	const approvals = items.find((item) => item.label === "Approvals")
	const waitlist = items.find((item) => item.label === "Waitlist")
	assert.deepEqual([approvals?.count, approvals?.dot], [3, true])
	assert.deepEqual([waitlist?.count, waitlist?.dot], [5, undefined])
	assert.equal(approvals?.to, "/manage/events/EV-1/approvals")
})

test("an empty queue shows no count or dot", () => {
	const items = managerNavigation({
		eventId: "EV-1",
		creatingEvent: false,
		hasSponsorships: false,
		requestCounts: { pending: 0, waiting: 0 },
	})
	const approvals = items.find((item) => item.label === "Approvals")
	assert.deepEqual([approvals?.count, approvals?.dot], [undefined, false])
})

test("a team offers its sections with settings last, scoped to its id", () => {
	const items = managerNavigation({ teamId: "T-1", creatingEvent: false, hasSponsorships: true })
	assert.deepEqual(labels(items), ["Calendar", "Members", "Payments", "Settings"])
	assert.ok(items.every((item) => item.to.startsWith("/manage/communities/T-1/")))
})

test("creating an event offers no destinations", () => {
	const items = managerNavigation({ creatingEvent: true, hasSponsorships: true })
	assert.deepEqual(items, [])
})

test("discover events leaves the dashboard for the public events page", () => {
	assert.equal(discoverEvents.href, "/events")
})

const guestsOnly = {
	details: "View",
	guests: "View",
	ticketing: null,
	talks: null,
	sponsors: null,
	communications: null,
} as const

test("a collaborator sees only the sections they were granted", () => {
	const items = managerNavigation({
		eventId: "EV-1",
		creatingEvent: false,
		hasSponsorships: false,
		access: guestsOnly,
	})
	assert.deepEqual(labels(items), ["Overview", "Details", "Guests", "Check-in"])
})

test("settings needs edit access to the event details", () => {
	const items = managerNavigation({
		eventId: "EV-1",
		creatingEvent: false,
		hasSponsorships: false,
		access: { ...guestsOnly, details: "Edit" },
	})
	assert.deepEqual(labels(items), ["Overview", "Details", "Guests", "Check-in", "Settings"])
})

test("approvals and waitlist need edit access to the guests", () => {
	const items = managerNavigation({
		eventId: "EV-1",
		creatingEvent: false,
		hasSponsorships: false,
		access: { ...guestsOnly, guests: "Edit" },
	})
	assert.deepEqual(labels(items), [
		"Overview",
		"Details",
		"Guests",
		"Approvals",
		"Waitlist",
		"Check-in",
	])
})

test("an event opens on the first section the user has", () => {
	assert.equal(firstEventPath("EV-1", guestsOnly), "/manage/events/EV-1/overview")
	assert.equal(
		firstEventPath("EV-1", { ...guestsOnly, details: null as never }),
		"/manage/events/EV-1/guests",
	)
})

test("transactions stay hidden from a guests-only collaborator", () => {
	const items = managerNavigation({
		eventId: "EV-1",
		creatingEvent: false,
		hasSponsorships: false,
		access: { ...guestsOnly, guests: "Edit", ticketing: "View", transactions: null },
	})
	assert.ok(!labels(items).includes("Transactions"))
})

test("transactions sit after payments once the user may view them", () => {
	const items = managerNavigation({
		eventId: "EV-1",
		creatingEvent: false,
		hasSponsorships: false,
		access: { ...guestsOnly, ticketing: "View", transactions: "View" },
	})
	assert.deepEqual(labels(items), [
		"Overview",
		"Details",
		"Tickets",
		"Payments",
		"Transactions",
		"Coupons",
		"Guests",
		"Check-in",
	])
	const transactions = items.find((item) => item.label === "Transactions")
	assert.equal(transactions?.to, "/manage/events/EV-1/transactions")
	assert.equal(transactions?.group, "Registration")
})
