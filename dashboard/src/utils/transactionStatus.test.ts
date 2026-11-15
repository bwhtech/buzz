import assert from "node:assert/strict"
import { test } from "node:test"

import {
	paymentStatusTheme,
	refundStatusTheme,
	transactionStatus,
	truncateMiddle,
} from "./transactionStatus.ts"

test("payment statuses map to their badge themes", () => {
	assert.equal(paymentStatusTheme("Paid"), "green")
	assert.equal(paymentStatusTheme("Verification Pending"), "amber")
	assert.equal(paymentStatusTheme(null), "gray")
})

test("refund statuses map to their badge themes", () => {
	assert.equal(refundStatusTheme("Refunded"), "red")
	assert.equal(refundStatusTheme("Partially Refunded"), "amber")
	assert.equal(refundStatusTheme("Something new"), "gray")
})

test("long references keep both ends, short ones stay whole", () => {
	assert.equal(truncateMiddle("pay_ABCDEFGHIJKLMNOP"), "pay_AB…KLMNOP")
	assert.equal(truncateMiddle("pay_123"), "pay_123")
})

test("a refund outranks the payment status", () => {
	assert.deepEqual(transactionStatus({ payment_status: "Paid", refund_status: "Refunded" }), {
		label: "Refunded",
		theme: "red",
	})
})

const unrefundedStatus = (payment_status: string | null) =>
	transactionStatus({ payment_status, refund_status: null })

test("an unrefunded booking shows its payment status", () => {
	assert.deepEqual(unrefundedStatus("Paid"), { label: "Paid", theme: "green" })
	assert.deepEqual(unrefundedStatus("Verification Pending"), {
		label: "Pending verification",
		theme: "amber",
	})
	assert.deepEqual(unrefundedStatus(null), { label: "Unpaid", theme: "gray" })
})
