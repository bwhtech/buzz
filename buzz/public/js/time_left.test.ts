import assert from "node:assert/strict"
import { test } from "node:test"

import { formatTimeLeft } from "./time_left.ts"

const SECOND = 1000
const MINUTE = 60 * SECOND
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

test("shows days, hours and minutes", () => {
	assert.equal(formatTimeLeft(63 * DAY + 5 * HOUR + 12 * MINUTE + 40 * SECOND), "63d 5h 12m")
})

test("keeps an empty hour between days and minutes", () => {
	assert.equal(formatTimeLeft(2 * DAY + 7 * MINUTE), "2d 0h 7m")
})

test("drops days under a day", () => {
	assert.equal(formatTimeLeft(5 * HOUR + 12 * MINUTE + 40 * SECOND), "5h 12m")
})

test("switches to minutes and seconds under an hour", () => {
	assert.equal(formatTimeLeft(12 * MINUTE + 8 * SECOND), "12m 08s")
})

test("floors at zero once the start has passed", () => {
	assert.equal(formatTimeLeft(-5 * SECOND), "0m 00s")
})
