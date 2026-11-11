import assert from "node:assert/strict"
import { test } from "node:test"

import { isRegistrationRequest, requestNotice, requestSubmitLabel } from "./registrationRequest.ts"

test("each request status has a notice, other statuses have none", () => {
	assert.equal(requestNotice("Requested")?.title, "Request received")
	assert.equal(requestNotice("Waitlisted")?.title, "You're on the waitlist")
	assert.equal(requestNotice("Rejected")?.theme, "red")
	assert.equal(requestNotice("Confirmed"), null)
	assert.equal(requestNotice(undefined), null)
})

test("only an approved paid booking can be paid", () => {
	assert.equal(requestNotice("Payment Pending")?.canPay, true)
	assert.equal(requestNotice("Requested")?.canPay, false)
})

test("a waitlisted or approval ticket makes the booking a request", () => {
	assert.equal(isRegistrationRequest([{}, { needs_approval: true }]), true)
	assert.equal(isRegistrationRequest([{ waitlisted: true }]), true)
	assert.equal(isRegistrationRequest([{}, {}]), false)
	assert.equal(isRegistrationRequest([]), false)
})

test("the waitlist label wins over the approval label", () => {
	assert.equal(
		requestSubmitLabel([{ needs_approval: true }, { waitlisted: true }]),
		"Join waitlist",
	)
	assert.equal(requestSubmitLabel([{ needs_approval: true }]), "Request to join")
	assert.equal(requestSubmitLabel([{}]), null)
})
