import assert from "node:assert/strict"
import { test } from "node:test"

import { groupEventsByMonth } from "./eventGroups.ts"

const event = (start_date: string, title = start_date) => ({ start_date, title })

test("events on the same date share a day group", () => {
	const groups = groupEventsByMonth([event("2026-08-15", "first"), event("2026-08-15", "second")])

	assert.equal(groups.length, 1)
	assert.deepEqual(
		groups[0].days.map((day) => day.date),
		["2026-08-15"],
	)
	assert.deepEqual(
		groups[0].days[0].events.map((row) => row.title),
		["first", "second"],
	)
})

test("dates split across months in input order", () => {
	const groups = groupEventsByMonth([event("2026-08-15"), event("2026-08-20"), event("2026-09-01")])

	assert.deepEqual(
		groups.map((group) => group.month),
		["2026-08", "2026-09"],
	)
	assert.deepEqual(
		groups[0].days.map((day) => day.date),
		["2026-08-15", "2026-08-20"],
	)
})

test("descending input keeps its order", () => {
	const groups = groupEventsByMonth([event("2026-09-01"), event("2026-08-20"), event("2026-08-15")])

	assert.deepEqual(
		groups.map((group) => group.month),
		["2026-09", "2026-08"],
	)
	assert.deepEqual(
		groups[1].days.map((day) => day.date),
		["2026-08-20", "2026-08-15"],
	)
})

test("no events produce no groups", () => {
	assert.deepEqual(groupEventsByMonth([]), [])
})
