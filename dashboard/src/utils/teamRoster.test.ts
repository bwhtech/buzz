import assert from "node:assert/strict"
import { test } from "node:test"

import type { TeamInvite, TeamMember } from "@/types"

import { matchesQuery, rosterRows } from "./teamRoster.ts"

const ada: TeamMember = {
	user: "ada@example.com",
	full_name: "Ada Lovelace",
	team_role: "Owner",
	user_image: null,
}

const grace: TeamInvite = { email: "grace@example.com", team_role: "Viewer" }

const team = { members: [ada], invites: [grace] }

const member = (user: string, team_role: string, full_name: string): TeamMember => ({
	user,
	full_name,
	team_role,
	user_image: null,
})

test("members come first, with pending invitations after them", () => {
	const rows = rosterRows(team)

	assert.deepEqual(
		rows.map((row) => row.key),
		["ada@example.com", "invite:grace@example.com"],
	)
})

test("each group runs from the most authority to the least", () => {
	const rows = rosterRows({
		members: [
			member("viewer@example.com", "Viewer", "Viewer"),
			member("owner@example.com", "Owner", "Owner"),
			member("desk@example.com", "Frontdesk", "Frontdesk"),
			member("admin@example.com", "Admin", "Admin"),
			member("manager@example.com", "Manager", "Manager"),
		],
		invites: [
			{ email: "invited-viewer@example.com", team_role: "Viewer" },
			{ email: "invited-admin@example.com", team_role: "Admin" },
		],
	})

	assert.deepEqual(
		rows.map((row) => row.role),
		["Owner", "Admin", "Manager", "Frontdesk", "Viewer", "Admin", "Viewer"],
	)
})

test("people sharing a role are listed alphabetically", () => {
	const rows = rosterRows({
		members: [
			member("zoe@example.com", "Manager", "Zoe"),
			member("abe@example.com", "Manager", "Abe"),
		],
		invites: [],
	})

	assert.deepEqual(
		rows.map((row) => row.name),
		["Abe", "Zoe"],
	)
})

test("an unknown role sorts last rather than first", () => {
	const rows = rosterRows({
		members: [
			member("overlord@example.com", "Overlord", "Overlord"),
			member("viewer@example.com", "Viewer", "Viewer"),
		],
		invites: [],
	})

	assert.deepEqual(
		rows.map((row) => row.role),
		["Viewer", "Overlord"],
	)
})

test("an invitation shows its address as its name and carries no member", () => {
	const [, invite] = rosterRows(team)

	assert.equal(invite.name, "grace@example.com")
	assert.equal(invite.member, undefined)
})

test("a search matches a name, an address or a role", () => {
	const [row] = rosterRows(team)

	assert.ok(matchesQuery(row, "lovelace"))
	assert.ok(matchesQuery(row, "ada@"))
	assert.ok(matchesQuery(row, "owner"))
	assert.ok(!matchesQuery(row, "grace"))
})
