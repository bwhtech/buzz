import assert from "node:assert/strict"
import { test } from "node:test"

import { NEW_PERSONAL_TEAM, eventTeamOptions } from "./eventTeamOptions.ts"

const community = { name: "T1", team_name: "Rust Club", team_role: "Manager", is_personal: false }
const viewed = { name: "T2", team_name: "Book Club", team_role: "Viewer", is_personal: false }
const personal = { name: "T3", team_name: "Noor Host", team_role: "Owner", is_personal: true }

test("lists only teams the user can create events in", () => {
	const options = eventTeamOptions([community, viewed], {
		personalTeamsEnabled: false,
		personalLabel: "Personal",
	})
	assert.deepEqual(options, [{ value: "T1", label: "Rust Club" }])
})

test("a personal team is labelled personal and listed first", () => {
	const options = eventTeamOptions([community, personal], {
		personalTeamsEnabled: true,
		personalLabel: "Personal",
	})
	assert.deepEqual(options, [
		{ value: "T3", label: "Personal" },
		{ value: "T1", label: "Rust Club" },
	])
})

test("offers to create a personal team when the user has none", () => {
	const options = eventTeamOptions([community], {
		personalTeamsEnabled: true,
		personalLabel: "Personal",
	})
	assert.deepEqual(options[0], { value: NEW_PERSONAL_TEAM, label: "Personal" })
})

test("offers no personal team while personal teams are off", () => {
	const options = eventTeamOptions([], { personalTeamsEnabled: false, personalLabel: "Personal" })
	assert.deepEqual(options, [])
})
