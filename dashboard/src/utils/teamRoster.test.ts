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

test("members come first, with pending invitations after them", () => {
	const rows = rosterRows(team)

	assert.deepEqual(
		rows.map((row) => row.key),
		["ada@example.com", "invite:grace@example.com"],
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
