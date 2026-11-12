import assert from "node:assert/strict"
import { test } from "node:test"

import { newInvitee, readyInvitees, splitEmails, tierFromSheet } from "./invites.ts"

const tiers = [
	{ value: "11", label: "General Admission" },
	{ value: "12", label: "VIP" },
]

test("typed text splits into addresses on any separator", () => {
	assert.deepEqual(splitEmails(" a@x.com, b@x.com;c@x.com\nd@x.com "), [
		"a@x.com",
		"b@x.com",
		"c@x.com",
		"d@x.com",
	])
})

test("a sheet tier matches a ticket type by title, a blank one takes the default", () => {
	assert.equal(tierFromSheet("vip", tiers, "11"), "12")
	assert.equal(tierFromSheet("", tiers, "11"), "11")
	assert.equal(tierFromSheet("Early Bird", tiers, "11"), "Early Bird")
})

test("only valid, first-seen rows on a known tier are ready", () => {
	const rows = [
		newInvitee({ email: "a@x.com", ticket_type: "11" }),
		newInvitee({ email: "A@x.com", ticket_type: "12" }),
		newInvitee({ email: "broken@", ticket_type: "11" }),
		newInvitee({ email: "c@x.com", ticket_type: "Early Bird" }),
	]
	assert.deepEqual(
		readyInvitees(rows, tiers).map((row) => row.email),
		["a@x.com"],
	)
})
