import assert from "node:assert/strict"
import { test } from "node:test"

import { discoverEvents, managerNavigation } from "./managerNavigation.ts"

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
	assert.equal(items.length, 7)
	assert.ok(items.every((item) => item.to.startsWith("/manage/events/EV-1/")))
})

test("a team offers its sections with settings last, scoped to its id", () => {
	const items = managerNavigation({ teamId: "T-1", creatingEvent: false, hasSponsorships: true })
	assert.deepEqual(labels(items), ["Events", "Members", "Payments", "Settings"])
	assert.ok(items.every((item) => item.to.startsWith("/manage/teams/T-1/")))
})

test("creating an event offers no destinations", () => {
	const items = managerNavigation({ creatingEvent: true, hasSponsorships: true })
	assert.deepEqual(items, [])
})

test("discover events leaves the dashboard for the public events page", () => {
	assert.equal(discoverEvents.href, "/events")
})
