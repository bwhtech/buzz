import assert from "node:assert/strict"
import { test } from "node:test"

import type { RegistrationRequest } from "../types.ts"
import { actionMessage, requestButtons, requestViewOf, viewAfter } from "./requestStatus.ts"

const row = (overrides: Partial<RegistrationRequest>): RegistrationRequest => ({
	name: "B-1",
	status: "Requested",
	request_type: "Approval",
	docstatus: 0,
	position: null,
	offer_expires_at: null,
	buyer_name: "Aarav Mehta",
	buyer_email: "aarav@example.com",
	total_amount: 0,
	currency: "INR",
	requested_at: "2026-11-01 10:00:00",
	attendees: [],
	answers: [],
	...overrides,
})

test("approval rows map to pending, awaiting, approved and declined", () => {
	assert.equal(requestViewOf(row({})), "pending")
	assert.equal(requestViewOf(row({ status: "Payment Pending", offer_expires_at: "x" })), "awaiting")
	assert.equal(requestViewOf(row({ status: "Confirmed", docstatus: 1 })), "approved")
	assert.equal(requestViewOf(row({ status: "Rejected" })), "declined")
})

test("a lapsed approval still reads awaiting payment", () => {
	assert.equal(requestViewOf(row({ status: "Payment Pending" })), "awaiting")
})

test("waitlist rows map to waiting, invited, expired, registered and removed", () => {
	const waitlist = (overrides: Partial<RegistrationRequest>) =>
		requestViewOf(row({ request_type: "Waitlist", ...overrides }))
	assert.equal(waitlist({ status: "Waitlisted" }), "waiting")
	assert.equal(waitlist({ status: "Payment Pending", offer_expires_at: "x" }), "invited")
	assert.equal(waitlist({ status: "Payment Pending", offer_expires_at: null }), "expired")
	assert.equal(waitlist({ status: "Confirmed", docstatus: 1 }), "registered")
	assert.equal(waitlist({ status: "Rejected" }), "removed")
})

test("approving moves a paid row to awaiting payment and a free one to approved", () => {
	assert.equal(viewAfter("approve", "Approval", true), "awaiting")
	assert.equal(viewAfter("approve", "Approval", false), "approved")
	assert.equal(viewAfter("approve", "Waitlist", true), "invited")
	assert.equal(viewAfter("revoke", "Waitlist", true), "waiting")
	assert.equal(viewAfter("decline", "Waitlist", false), "removed")
})

const labels = (view: Parameters<typeof requestButtons>[0], paid = false) =>
	requestButtons(view, paid).map((button) => button.label)

test("the drawer offers the design's buttons per status", () => {
	assert.deepEqual(labels("pending", true), ["Approve & send link", "Decline"])
	assert.deepEqual(labels("declined"), ["Approve anyway", "Move to pending"])
	assert.deepEqual(labels("expired"), ["Invite again", "Back to waitlist"])
	assert.deepEqual(labels("approved"), [])
	assert.deepEqual(labels("registered"), [])
})

test("toasts name one person or count many", () => {
	const subject = { type: "Approval" as const, names: ["Aarav"], price: "₹1,500" }
	assert.equal(actionMessage("approve", subject), "Approved Aarav · ₹1,500 payment link sent")
	assert.equal(
		actionMessage("approve", { ...subject, names: ["Aarav", "Diya"] }),
		"Approved 2 requests",
	)
	assert.equal(
		actionMessage("decline", { ...subject, type: "Waitlist" }),
		"Removed Aarav from the waitlist",
	)
	assert.equal(actionMessage("revoke", subject), "Moved Aarav back to pending")
})
