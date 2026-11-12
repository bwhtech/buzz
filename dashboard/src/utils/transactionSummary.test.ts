import assert from "node:assert/strict"
import { test } from "node:test"

import type { CurrencySummary, TransactionSummary } from "../types.ts"
import { transactionSummaryCards } from "./transactionSummary.ts"

const currency = (overrides: Partial<CurrencySummary>): CurrencySummary => ({
	currency: "INR",
	collected: 12000,
	refunded: 2000,
	net: 10000,
	tax: 1800,
	discounts: 500,
	bookings: 8,
	tickets: 11,
	average_order_value: 1500,
	...overrides,
})

const summary = (overrides: Partial<TransactionSummary> = {}): TransactionSummary => ({
	currencies: [currency({})],
	pending_verification: [],
	by_payment_method: [],
	...overrides,
})

const titles = (cards: { title: string }[]) => cards.map((card) => card.title)

test("a currency reads net, gross, refunds, bookings and the average order", () => {
	const [set] = transactionSummaryCards(summary())
	assert.deepEqual(titles(set.cards), [
		"Net revenue",
		"Gross collected",
		"Refunded",
		"Paid bookings",
		"Average order value",
	])
	assert.equal(set.cards[0].value, "₹10,000")
	assert.equal(set.cards[3].caption, "11 tickets sold")
	assert.equal(set.footnote, "₹1,800 tax · ₹500 discounts")
})

test("pending verification shows only for the currency that has some", () => {
	const sets = transactionSummaryCards(
		summary({
			currencies: [currency({}), currency({ currency: "USD", bookings: 2 })],
			pending_verification: [{ currency: "INR", bookings: 1, amount: 900 }],
		}),
	)
	assert.deepEqual(
		sets.map((set) => set.currency),
		["INR", "USD"],
	)
	assert.equal(sets[0].cards.at(-1)?.title, "Pending verification")
	assert.equal(sets[0].cards.at(-1)?.caption, "1 booking")
	assert.ok(!titles(sets[1].cards).includes("Pending verification"))
})

test("the busiest currency comes first", () => {
	const sets = transactionSummaryCards(
		summary({
			currencies: [currency({ bookings: 1 }), currency({ currency: "USD", bookings: 5 })],
		}),
	)
	assert.equal(sets[0].currency, "USD")
})
