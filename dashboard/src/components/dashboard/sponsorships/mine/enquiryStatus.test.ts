import assert from "node:assert/strict"
import { test } from "node:test"

import { enquiryActions, enquiryStatusIcon, enquiryStatusMessage } from "./enquiryStatus.ts"

test("only an approved enquiry can be paid", () => {
	assert.equal(enquiryActions("Payment Pending").canPay, true)
	assert.equal(enquiryActions("Approval Pending").canPay, false)
	assert.equal(enquiryActions("Paid").canPay, false)
})

test("a settled enquiry cannot be withdrawn or get a new logo", () => {
	for (const status of ["Paid", "Cancelled", "Withdrawn"]) {
		assert.equal(enquiryActions(status).canWithdraw, false, status)
		assert.equal(enquiryActions(status).canChangeLogo, false, status)
	}
	assert.equal(enquiryActions("Approval Pending").canWithdraw, true)
	assert.equal(enquiryActions("Payment Pending").canWithdraw, true)
})

test("a status the app does not know says nothing about it", () => {
	assert.equal(enquiryStatusMessage("On Hold"), "")
	assert.equal(enquiryStatusIcon("On Hold"), "lucide-squircle-dashed")
})
