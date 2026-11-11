import assert from "node:assert/strict"
import { test } from "node:test"

import {
	approvalModeOf,
	approvalModeWrites,
	approvalSwitch,
	waitlistSwitch,
} from "./approvalMode.ts"

const general = { name: "1", requires_approval: false }
const workshop = { name: "2", requires_approval: true }

test("the event flag means manual review, whatever the tickets say", () => {
	assert.equal(approvalModeOf(true, [general]), "manual")
	assert.equal(approvalModeOf(true, [workshop]), "manual")
})

test("a flagged ticket type without the event flag means review some", () => {
	assert.equal(approvalModeOf(false, [general, workshop]), "some")
})

test("no flag anywhere means auto-confirm", () => {
	assert.equal(approvalModeOf(false, [general]), "auto")
	assert.equal(approvalModeOf(false, []), "auto")
})

test("manual review turns the event flag on and leaves ticket types alone", () => {
	assert.deepEqual(approvalModeWrites("manual", [general, workshop]), {
		requires_approval: true,
		clearTicketTypes: [],
	})
})

test("review some turns the event flag off and keeps ticket type flags", () => {
	assert.deepEqual(approvalModeWrites("some", [workshop]), {
		requires_approval: false,
		clearTicketTypes: [],
	})
})

test("auto-confirm clears the event flag and every flagged ticket type", () => {
	assert.deepEqual(approvalModeWrites("auto", [general, workshop]), {
		requires_approval: false,
		clearTicketTypes: ["2"],
	})
})

test("the ticket approval switch is only free under review some", () => {
	assert.equal(approvalSwitch("some").disabled, false)
	assert.deepEqual([approvalSwitch("manual").forced, approvalSwitch("auto").forced], [true, false])
})

test("the ticket waitlist switch needs a seat limit and follows the event waitlist", () => {
	assert.equal(waitlistSwitch(false, false).disabled, true)
	assert.equal(waitlistSwitch(true, false).forced, false)
	assert.equal(waitlistSwitch(true, true).forced, true)
	assert.equal(waitlistSwitch(false, true).disabled, false)
})
