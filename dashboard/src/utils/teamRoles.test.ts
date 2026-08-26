import assert from "node:assert/strict"
import { test } from "node:test"
import { canCreateEvents } from "./teamRoles.ts"

test("a manager can create events", () => {
	assert.equal(canCreateEvents("Manager"), true)
})

test("an admin and an owner can create events", () => {
	assert.equal(canCreateEvents("Admin"), true)
	assert.equal(canCreateEvents("Owner"), true)
})

test("a viewer cannot create events", () => {
	assert.equal(canCreateEvents("Viewer"), false)
})

test("a frontdesk member cannot create events", () => {
	assert.equal(canCreateEvents("Frontdesk"), false)
})

test("no team selected cannot create events", () => {
	assert.equal(canCreateEvents(undefined), false)
})
