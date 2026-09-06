import assert from "node:assert/strict"
import { test } from "node:test"

import type { TeamOption } from "../types.ts"
import { canCreateEvents, canManageMembers, hostableTeams } from "./teamRoles.ts"

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

const team = (name: string, team_role: string): TeamOption => ({
	name,
	team_name: name,
	logo: null,
	team_role,
	members: [],
})

test("only teams that can create events can host one", () => {
	const hostable = hostableTeams([
		team("BTEAM-0001", "Owner"),
		team("BTEAM-0002", "Viewer"),
		team("BTEAM-0003", "Manager"),
		team("BTEAM-0004", "Frontdesk"),
		team("BTEAM-0005", "Admin"),
	])
	assert.deepEqual(
		hostable.map((option) => option.name),
		["BTEAM-0001", "BTEAM-0003", "BTEAM-0005"],
	)
})

test("no teams means nothing to host with", () => {
	assert.deepEqual(hostableTeams([]), [])
})
