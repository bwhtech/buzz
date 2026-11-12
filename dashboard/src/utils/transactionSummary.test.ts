import assert from "node:assert/strict"
import { test } from "node:test"

import type { CurrencySummary, DailyRevenue, TransactionSummary } from "../types.ts"
import {
	currenciesByVolume,
	groupIntoBars,
	paymentMethodShares,
	percentChange,
	periodStats,
	summaryFootnote,
} from "./transactionSummary.ts"

const money = (amount: number, currency: string) => `${currency} ${amount}`

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

const day = (date: string, collected: number, bookings: number, refunded = 0): DailyRevenue => ({
	date,
	currency: "INR",
	collected,
	refunded,
	bookings,
})

const summary = (overrides: Partial<TransactionSummary> = {}): TransactionSummary => ({
	currencies: [currency({})],
	daily: [],
	pending_verification: [],
	by_payment_method: [],
	...overrides,
})

test("a week sums its own days and compares with the week before", () => {
	const data = summary({
		daily: [day("2026-11-01", 500, 1), day("2026-11-10", 1000, 2, 100), day("2026-11-13", 300, 1)],
	})
	const week = periodStats(data, "INR", "7d", "2026-11-13")

	assert.equal(week.net, 1200)
	assert.equal(week.bookings, 3)
	assert.equal(week.averageOrder, 1300 / 3)
	assert.equal(week.previousNet, 500)
	assert.deepEqual(week.bookingBars, [0, 0, 0, 2, 0, 0, 1])
	assert.deepEqual(week.netRunning, [0, 0, 0, 900, 900, 900, 1200])
})

test("all time starts at the first sale and has nothing to compare with", () => {
	const data = summary({ daily: [day("2026-11-11", 500, 1), day("2026-11-13", 300, 1)] })
	const all = periodStats(data, "INR", "all", "2026-11-13")

	assert.deepEqual(all.netRunning, [500, 500, 800])
	assert.equal(all.previousNet, null)
	assert.equal(percentChange(all.net, all.previousNet), null)
})

test("an event with no sales reads zero", () => {
	const all = periodStats(summary(), "INR", "all", "2026-11-13")
	assert.deepEqual([all.net, all.bookings, all.averageOrder], [0, 0, 0])
})

test("a long range groups its days into at most thirty bars", () => {
	const bars = groupIntoBars(Array.from({ length: 90 }, () => 1))
	assert.equal(bars.length, 30)
	assert.ok(bars.every((bar) => bar === 3))
	assert.deepEqual(groupIntoBars([1, 2, 3]), [1, 2, 3])
})

test("percent change rounds to one decimal", () => {
	assert.equal(percentChange(150, 120), 25)
	assert.equal(percentChange(100, 300), -66.7)
})

test("the busiest currency comes first", () => {
	const data = summary({
		currencies: [currency({ bookings: 1 }), currency({ currency: "USD", bookings: 5 })],
	})
	assert.deepEqual(currenciesByVolume(data), ["USD", "INR"])
	assert.equal(summaryFootnote(data, "INR", money), "All time: INR 1800 tax · INR 500 discounts")
})

test("payment methods split one currency's amount, largest first", () => {
	const data = summary({
		by_payment_method: [
			{ currency: "INR", payment_method: "Razorpay", bookings: 1, amount: 250 },
			{ currency: "INR", payment_method: null, bookings: 3, amount: 750 },
			{ currency: "USD", payment_method: "Stripe", bookings: 2, amount: 400 },
		],
	})
	assert.deepEqual(paymentMethodShares(data, "INR"), [
		{ method: "Other", amount: 750, bookings: 3, percent: 75 },
		{ method: "Razorpay", amount: 250, bookings: 1, percent: 25 },
	])
})
