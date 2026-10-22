import assert from "node:assert/strict"
import { test } from "node:test"

import type { CouponItem, CouponTicketType } from "@/types"

import {
	conditionLabel,
	couponStats,
	discountLabel,
	endsLabel,
	statusLabel,
	usedLabel,
	scopeLabel,
	statusTheme,
} from "./couponLabels.ts"

const ticketTypes: CouponTicketType[] = [
	{ name: "1", title: "Student", prices: [{ currency: "INR", price: 500 }] },
	{ name: "2", title: "VIP", prices: [{ currency: "INR", price: 5000 }] },
]

function coupon(overrides: Partial<CouponItem> = {}): CouponItem {
	return {
		name: "c1",
		coupon_type: "Promo Code",
		code: "EARLYBIRD",
		description: null,
		enabled: true,
		discount_type: "Percentage",
		discount_percentage: 20,
		discount_amounts: [],
		applies_to_all_ticket_types: true,
		ticket_types: [],
		minimum_requirement: "None",
		minimum_order_amounts: [],
		minimum_ticket_count: 0,
		usage_limit: 0,
		once_per_buyer: false,
		starts_on: null,
		expires_on: null,
		times_used: 0,
		status: "Active",
		...overrides,
	}
}

test("a percentage reads as a share off", () => {
	assert.equal(discountLabel(coupon()), "20% off")
})

test("a flat amount lists every currency", () => {
	const amounts = [
		{ currency: "INR", price: 250 },
		{ currency: "USD", price: 3 },
	]
	assert.equal(
		discountLabel(coupon({ discount_type: "Flat Amount", discount_amounts: amounts })),
		"₹250 · $3 off",
	)
})

test("scope names the picked ticket types", () => {
	assert.equal(scopeLabel(coupon(), ticketTypes), "All tickets")
	const picked = coupon({ applies_to_all_ticket_types: false, ticket_types: ["2", "1"] })
	assert.equal(scopeLabel(picked, ticketTypes), "Student, VIP")
})

test("only an active coupon is green", () => {
	assert.equal(statusTheme("Active"), "green")
	assert.equal(statusTheme("Used up"), "gray")
	assert.equal(statusTheme("Scheduled"), "blue")
})

test("stats count active coupons, redemptions and the amount discounted", () => {
	const coupons = [coupon({ times_used: 3 }), coupon({ status: "Disabled", times_used: 2 })]
	const discounted = [
		{ currency: "INR", amount: 1500 },
		{ currency: "USD", amount: 20 },
	]
	assert.deepEqual(couponStats(coupons, discounted), [
		{ label: "Active coupons", value: "1" },
		{ label: "Redemptions", value: "5" },
		{ label: "Discounted", value: "₹1,500 · $20" },
	])
})

test("the condition names a ticket count or a minimum order per currency", () => {
	assert.equal(conditionLabel(coupon()), null)
	assert.equal(
		conditionLabel(
			coupon({ minimum_requirement: "Minimum Ticket Count", minimum_ticket_count: 5 }),
		),
		"5+ tickets",
	)
	const amounts = [
		{ currency: "INR", price: 2000 },
		{ currency: "USD", price: 25 },
	]
	assert.equal(
		conditionLabel(
			coupon({ minimum_requirement: "Minimum Order Amount", minimum_order_amounts: amounts }),
		),
		"Orders from ₹2,000 / $25",
	)
})

test("a card says when the coupon ends", () => {
	assert.equal(endsLabel(coupon({ expires_on: "2026-11-15" })), "Ends 15 Nov")
	assert.equal(endsLabel(coupon({ expires_on: "2026-09-30" })), "Ends 30 Sep")
	assert.equal(endsLabel(coupon()), "No end date")
})

test("usage reads against the limit when there is one", () => {
	assert.equal(usedLabel(coupon({ times_used: 34, usage_limit: 100 })), "34 / 100 used")
	assert.equal(usedLabel(coupon({ times_used: 3 })), "3 used")
})

test("a scheduled coupon's badge says when it starts", () => {
	assert.equal(
		statusLabel(coupon({ status: "Scheduled", starts_on: "2026-12-01" })),
		"Starts 1 Dec",
	)
	assert.equal(statusLabel(coupon({ status: "Used up" })), "Used up")
})
