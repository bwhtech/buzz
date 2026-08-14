import assert from "node:assert/strict"
import { test } from "node:test"
import { alignedEndDate } from "./eventDates.ts"

test("an unset end date follows the start", () => {
	assert.equal(alignedEndDate("2026-08-21", ""), "2026-08-21")
})

test("an end date behind the start is pulled up to it", () => {
	assert.equal(alignedEndDate("2026-08-21", "2026-08-19"), "2026-08-21")
})

test("a multi-day span survives a start moved within it", () => {
	assert.equal(alignedEndDate("2026-08-21", "2026-08-23"), "2026-08-23")
})

test("an end date on the start date stays put", () => {
	assert.equal(alignedEndDate("2026-08-21", "2026-08-21"), "2026-08-21")
})

test("clearing the start leaves the end alone", () => {
	assert.equal(alignedEndDate("", "2026-08-23"), "2026-08-23")
})
