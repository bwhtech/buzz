import assert from "node:assert/strict"
import { test } from "node:test"

import {
	describeLevels,
	emptySectionLevels,
	grantedSections,
	opensAPage,
	setAllLevels,
} from "./eventSections.ts"

test("a new collaborator can view only the details", () => {
	assert.deepEqual(describeLevels(emptySectionLevels()), [{ level: "View", labels: ["Details"] }])
})

test("edit and view are listed separately", () => {
	const levels = { ...emptySectionLevels(), guests_access: "Edit", talks_access: "View" } as const
	assert.deepEqual(describeLevels(levels), [
		{ level: "Edit", labels: ["Guests"] },
		{ level: "View", labels: ["Details", "Talks"] },
	])
})

test("every section at one level reads as a whole", () => {
	const levels = emptySectionLevels()
	setAllLevels(levels, "Edit")
	assert.deepEqual(describeLevels(levels), [{ level: "Edit", labels: null }])
})

test("only granted sections become chips", () => {
	const levels = { ...emptySectionLevels(), sponsors_access: "Edit" } as const
	assert.deepEqual(
		grantedSections(levels).map((section) => [section.key, section.level]),
		[
			["details", "View"],
			["sponsors", "Edit"],
		],
	)
})

test("details view alone opens no page", () => {
	assert.equal(opensAPage(emptySectionLevels()), false)
	assert.equal(opensAPage({ ...emptySectionLevels(), details_access: "Edit" }), true)
	assert.equal(opensAPage({ ...emptySectionLevels(), talks_access: "View" }), true)
})
