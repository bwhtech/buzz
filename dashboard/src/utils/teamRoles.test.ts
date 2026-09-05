import assert from "node:assert/strict"
import { test } from "node:test"

import { canCreateEvents, canManageMembers } from "./teamRoles.ts"

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

test("an owner and an admin can manage members", () => {
	assert.equal(canManageMembers("Owner"), true)
	assert.equal(canManageMembers("Admin"), true)
})

test("a manager cannot manage members", () => {
	assert.equal(canManageMembers("Manager"), false)
	assert.equal(canManageMembers(undefined), false)
})
