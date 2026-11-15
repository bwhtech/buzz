import assert from "node:assert/strict"
import { test } from "node:test"

import type { TransactionLineItem } from "../types.ts"
import { breakdownLines } from "./transactionBreakdown.ts"

const item = (
	ticket_type: string,
	amount: number,
	add_on_items: { title: string; price: number }[] = [],
): TransactionLineItem => ({
	attendee_name: "Ananya Rao",
	attendee_email: "ananya@example.com",
	ticket_type,
	amount,
	add_ons: add_on_items.map((addOn) => addOn.title),
	add_on_items,
	add_on_total: add_on_items.reduce((sum, addOn) => sum + addOn.price, 0),
})

test("tickets of one type and price collapse into one counted line, add-ons after", () => {
	const lunch = { title: "Lunch", price: 350 }
	const lines = breakdownLines([
		item("General", 1499, [lunch]),
		item("General", 1499),
		item("VIP", 4999, [lunch, { title: "T-shirt", price: 499 }]),
	])

	assert.deepEqual(
		lines.map(({ label, count, unitPrice, addOn }) => [label, count, unitPrice, addOn]),
		[
			["General", 2, 1499, false],
			["VIP", 1, 4999, false],
			["Lunch", 2, 350, true],
			["T-shirt", 1, 499, true],
		],
	)
})

test("the same type at a different price stays its own line", () => {
	const lines = breakdownLines([item("General", 1499), item("General", 999)])
	assert.equal(lines.length, 2)
})
