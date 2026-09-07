import assert from "node:assert/strict"
import { test } from "node:test"

import { matches, restoredDraft } from "./formDraft.ts"

const baseline = { title: "Frappe Fest", venue: "" }
const edited = { title: "Frappe Fest 2026", venue: "" }

test("two snapshots of the same values match", () => {
	assert.equal(matches(baseline, { title: "Frappe Fest", venue: "" }), true)
})

test("a changed field breaks the match", () => {
	assert.equal(matches(baseline, edited), false)
})

test("nothing stored means nothing to restore", () => {
	assert.deepEqual(restoredDraft({}, baseline), { status: "none" })
})

test("edits typed against this document come back", () => {
	assert.deepEqual(restoredDraft({ baseline, form: edited }, baseline), {
		status: "restored",
		form: edited,
	})
})

test("a draft matching the document is not an edit", () => {
	assert.deepEqual(restoredDraft({ baseline, form: { ...baseline } }, baseline), {
		status: "none",
	})
})

test("a draft typed against an older document reads as stale", () => {
	const moved = { title: "Frappe Fest", venue: "Bengaluru" }
	assert.deepEqual(restoredDraft({ baseline, form: edited }, moved), { status: "stale" })
})

test("a half-written entry without its baseline is dropped", () => {
	assert.deepEqual(restoredDraft({ form: edited }, baseline), { status: "none" })
})
