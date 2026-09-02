import assert from "node:assert/strict"
import { test } from "node:test"

import type { ProposalListItem } from "../types.ts"
import { proposalActions } from "./proposalActions.ts"

const TODAY = "2026-06-15"

const proposal = (fields: Partial<ProposalListItem> = {}): ProposalListItem => ({
	name: "p1",
	title: "A talk",
	event: "e1",
	event_title: "An event",
	start_date: "2026-07-01",
	end_date: "2026-07-01",
	banner_image: null,
	allow_editing_talks_after_acceptance: false,
	status: "Review Pending",
	creation: "2026-06-01 10:00:00",
	modified: "2026-06-01 10:00:00",
	speakers: [],
	...fields,
})

test("a pending proposal on an upcoming event is fully open", () => {
	assert.deepEqual(proposalActions(proposal(), TODAY), {
		canEdit: true,
		canWithdraw: true,
		canManageSpeakers: true,
	})
})

test("an accepted proposal is closed unless its event allows edits after acceptance", () => {
	assert.equal(proposalActions(proposal({ status: "Accepted" }), TODAY).canEdit, false)

	const open = proposalActions(
		proposal({ status: "Accepted", allow_editing_talks_after_acceptance: true }),
		TODAY,
	)
	assert.deepEqual(open, { canEdit: true, canWithdraw: false, canManageSpeakers: false })
})

test("every other status is closed", () => {
	for (const status of ["Shortlisted", "Rejected", "Replied", "Duplicate", "Withdrawn"]) {
		assert.deepEqual(proposalActions(proposal({ status }), TODAY), {
			canEdit: false,
			canWithdraw: false,
			canManageSpeakers: false,
		})
	}
})

test("the event ending closes a pending proposal", () => {
	const over = proposal({ start_date: "2026-06-01", end_date: "2026-06-14" })
	assert.deepEqual(proposalActions(over, TODAY), {
		canEdit: false,
		canWithdraw: false,
		canManageSpeakers: false,
	})
})

test("an event running through today is not over", () => {
	const running = proposal({ start_date: "2026-06-01", end_date: TODAY })
	assert.equal(proposalActions(running, TODAY).canWithdraw, true)
})

test("a multi-day event is judged by its end, not its start", () => {
	const running = proposal({ start_date: "2026-06-01", end_date: "2026-06-20" })
	assert.equal(proposalActions(running, TODAY).canWithdraw, true)
})
