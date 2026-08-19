import assert from "node:assert/strict"
import { test } from "node:test"
import { inTab } from "./timelineTabs.ts"

const TODAY = "2026-08-13"

const item = (start_date: string) => ({ start_date })

test("today counts as upcoming", () => {
	assert.deepEqual(inTab([item(TODAY)], "upcoming", TODAY), [item(TODAY)])
	assert.deepEqual(inTab([item(TODAY)], "past", TODAY), [])
})

test("upcoming comes back soonest first", () => {
	const items = [item("2026-09-01"), item("2026-08-14"), item("2026-08-20")]

	assert.deepEqual(
		inTab(items, "upcoming", TODAY).map((row) => row.start_date),
		["2026-08-14", "2026-08-20", "2026-09-01"],
	)
})

test("past comes back newest first", () => {
	const items = [item("2026-07-01"), item("2026-08-12"), item("2026-06-15")]

	assert.deepEqual(
		inTab(items, "past", TODAY).map((row) => row.start_date),
		["2026-08-12", "2026-07-01", "2026-06-15"],
	)
})

test("no items produce no rows", () => {
	assert.deepEqual(inTab([], "upcoming", TODAY), [])
})

test("a multi-day row running through today is still upcoming", () => {
	const running = { start_date: "2026-08-10", end_date: "2026-08-13" }

	assert.deepEqual(inTab([running], "upcoming", TODAY), [running])
	assert.deepEqual(inTab([running], "past", TODAY), [])
})

test("a multi-day row that ended is past, sorted by its start", () => {
	const ended = { start_date: "2026-08-10", end_date: "2026-08-12" }

	assert.deepEqual(inTab([ended], "past", TODAY), [ended])
	assert.deepEqual(inTab([ended], "upcoming", TODAY), [])
})

test("a null end_date falls back to start_date", () => {
	const row = { start_date: "2026-08-12", end_date: null }

	assert.deepEqual(inTab([row], "past", TODAY), [row])
})
