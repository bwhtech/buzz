import assert from "node:assert/strict"
import { test } from "node:test"

import { alignedEndDate, isEndBeforeStart } from "./eventDates.ts"

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

test("an end time after the start on a single-day event is fine", () => {
	assert.equal(isEndBeforeStart("2026-08-21", "", "09:00:00", "17:00:00"), false)
})

test("an end time before the start on a single-day event is caught", () => {
	assert.equal(isEndBeforeStart("2026-08-21", "", "17:00:00", "09:00:00"), true)
})

test("an end time equal to the start is caught", () => {
	assert.equal(isEndBeforeStart("2026-08-21", "", "09:00:00", "09:00:00"), true)
})

test("an explicit end date matching the start is still a single day", () => {
	assert.equal(isEndBeforeStart("2026-08-21", "2026-08-21", "17:00:00", "09:00:00"), true)
})

test("a multi-day event may end earlier in the day than it started", () => {
	assert.equal(isEndBeforeStart("2026-08-21", "2026-08-23", "17:00:00", "09:00:00"), false)
})

test("the short and long time formats compare the same", () => {
	assert.equal(isEndBeforeStart("2026-08-21", "", "09:00", "17:00:00"), false)
	assert.equal(isEndBeforeStart("2026-08-21", "", "17:00:00", "09:00"), true)
})

test("a half-filled schedule is not reported as invalid", () => {
	assert.equal(isEndBeforeStart("2026-08-21", "", "", "09:00:00"), false)
	assert.equal(isEndBeforeStart("2026-08-21", "", "09:00:00", ""), false)
})
