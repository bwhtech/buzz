import assert from "node:assert/strict"
import { test } from "node:test"

import {
	approvalModeOf,
	approvalModeWrites,
	accessChanged,
	withEventAccess,
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

test("the ticket type switches include what the event decides", () => {
	const values = { requires_approval: false, enable_waitlist: false }
	assert.deepEqual(withEventAccess(values, { mode: "manual", eventWaitlist: true }), {
		requires_approval: true,
		enable_waitlist: true,
	})
	assert.deepEqual(withEventAccess(values, { mode: "some", eventWaitlist: false }), values)
})

test("access counts as changed only when a switch moved", () => {
	const values = { requires_approval: true, enable_waitlist: false }
	assert.equal(accessChanged(values, { ...values }), false)
	assert.equal(accessChanged(values, { ...values, enable_waitlist: true }), true)
})
