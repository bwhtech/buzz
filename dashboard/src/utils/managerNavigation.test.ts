import assert from "node:assert/strict"
import { test } from "node:test"

import { managerNavigation } from "./managerNavigation.ts"

const labels = (items: { label: string }[]) => items.map((item) => item.label)

test("the root offers events and proposals", () => {
	const items = managerNavigation({ creatingEvent: false, hasSponsorships: false })
	assert.deepEqual(labels(items), ["Events", "Talk Proposals"])
})

test("sponsorship appears once the user has an inquiry", () => {
	const items = managerNavigation({ creatingEvent: false, hasSponsorships: true })
	assert.deepEqual(labels(items), ["Events", "Talk Proposals", "Sponsorship"])
})

test("an event offers its own sections, scoped to its id", () => {
	const items = managerNavigation({ eventId: "EV-1", creatingEvent: false, hasSponsorships: true })
	assert.equal(items.length, 6)
	assert.ok(items.every((item) => item.to.startsWith("/manage/events/EV-1/")))
})

test("creating an event offers no destinations", () => {
	const items = managerNavigation({ creatingEvent: true, hasSponsorships: true })
	assert.deepEqual(items, [])
})
