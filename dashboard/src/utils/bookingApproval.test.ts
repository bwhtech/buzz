import assert from "node:assert/strict"
import { test } from "node:test"

import {
	approvalResultMessage,
	approvalState,
	bookingStatusBadge,
	needsApproval,
} from "./bookingApproval.ts"

test("approval states need requires_approval, except withdrawn and expired", () => {
	assert.equal(approvalState({ status: "Approval Pending", requires_approval: true }), "pending")
	assert.equal(approvalState({ status: "Rejected", requires_approval: true }), "declined")
	assert.equal(approvalState({ status: "Withdrawn" }), "withdrawn")
	assert.equal(approvalState({ status: "Expired" }), "expired")
})

test("offline payment statuses are not approval states", () => {
	assert.equal(approvalState({ status: "Approval Pending", requires_approval: false }), null)
	assert.equal(approvalState({ status: "Rejected" }), null)
	assert.equal(approvalState({ status: "Confirmed", requires_approval: true }), null)
})

test("status badges name the new statuses", () => {
	assert.deepEqual(bookingStatusBadge("Rejected"), { label: "Declined", theme: "red" })
	assert.deepEqual(bookingStatusBadge("Withdrawn"), { label: "Withdrawn", theme: "gray" })
	assert.deepEqual(bookingStatusBadge("Approval Pending"), {
		label: "Pending approval",
		theme: "amber",
	})
})

test("the event-wide switch or any chosen ticket type makes a booking need approval", () => {
	const byType = { vip: true, general: false }
	assert.equal(needsApproval(true, ["general"], byType), true)
	assert.equal(needsApproval(false, ["general", "vip"], byType), true)
	assert.equal(needsApproval(false, ["general"], byType), false)
	assert.equal(needsApproval(false, [], byType), false)
})

test("a partial approval names how many did not fit", () => {
	assert.equal(
		approvalResultMessage({ approved: 15, failed: 5, declined: 0 }),
		"15 approved, 5 couldn't fit — still pending",
	)
	assert.equal(approvalResultMessage({ approved: 0, failed: 0, declined: 0 }), null)
})
