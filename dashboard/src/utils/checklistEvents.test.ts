import assert from "node:assert/strict"
import { test } from "node:test"

import { checklistEvents } from "./checklistEvents.ts"

const create = { step: "create_event", group: "launch" }
const book = { step: "book_ticket", group: "attendee" }

test("the first load is a baseline", () => {
	assert.deepEqual(checklistEvents(null, [create], ["create_event"]), [])
})

test("a newly done step is sent once", () => {
	assert.deepEqual(checklistEvents([], [create], ["create_event", "book_ticket"]), [
		["checklist_step_completed", create],
	])
	assert.deepEqual(checklistEvents(["create_event"], [create], ["create_event", "book_ticket"]), [])
})

test("finishing the last essential completes the checklist", () => {
	assert.deepEqual(
		checklistEvents(["create_event"], [create, book], ["create_event", "book_ticket"]),
		[["checklist_step_completed", book], ["checklist_completed"]],
	)
})

test("a checklist already complete is not completed again", () => {
	const events = checklistEvents(
		["create_event"],
		[create, { step: "extra", group: "launch" }],
		["create_event"],
	)
	assert.deepEqual(events, [["checklist_step_completed", { step: "extra", group: "launch" }]])
})
