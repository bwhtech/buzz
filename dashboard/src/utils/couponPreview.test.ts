import assert from "node:assert/strict"
import { test } from "node:test"

import type { CouponTicketType } from "@/types"

import { blankCouponValues } from "./couponForm.ts"
import { checkoutPreview } from "./couponPreview.ts"

const ticketTypes: CouponTicketType[] = [
	{ name: "student", title: "Student", prices: [{ currency: "INR", price: 500 }] },
	{
		name: "vip",
		title: "VIP",
		prices: [
			{ currency: "INR", price: 5000 },
			{ currency: "USD", price: 60 },
		],
	},
]

const values = (overrides = {}) => ({
	...blankCouponValues(),
	code: "SAVE",
	discount_percentage: 20,
	...overrides,
})

test("a percentage previews one of the first eligible ticket", () => {
	const preview = checkoutPreview(values(), ticketTypes, {})
	assert.deepEqual(
		{ ...preview, note: undefined },
		{
			ticketType: "student",
			currency: "INR",
			quantity: 1,
			subtotal: 500,
			discount: 100,
			total: 400,
			note: undefined,
		},
	)
})

test("the picked ticket type and currency are previewed", () => {
	const preview = checkoutPreview(values(), ticketTypes, { ticketType: "vip", currency: "USD" })
	assert.deepEqual([preview?.subtotal, preview?.discount], [60, 12])
})

test("a ticket count minimum previews that many tickets", () => {
	const preview = checkoutPreview(
		values({ minimum_requirement: "Minimum Ticket Count", minimum_ticket_count: 5 }),
		ticketTypes,
		{},
	)
	assert.deepEqual([preview?.quantity, preview?.subtotal], [5, 2500])
})

test("an order minimum previews enough tickets to reach it", () => {
	const preview = checkoutPreview(
		values({
			minimum_requirement: "Minimum Order Amount",
			minimum_order_amounts: [{ currency: "INR", price: 1200 }],
		}),
		ticketTypes,
		{},
	)
	assert.equal(preview?.quantity, 3)
})

test("a fixed amount is capped at the order total", () => {
	const preview = checkoutPreview(
		values({ discount_type: "Flat Amount", discount_amounts: [{ currency: "INR", price: 800 }] }),
		ticketTypes,
		{},
	)
	assert.deepEqual([preview?.discount, preview?.total], [500, 0])
	assert.equal(preview?.note, "The discount is capped at the order total.")
})

test("nothing to preview without an eligible ticket type", () => {
	assert.equal(
		checkoutPreview(values({ applies_to_all_ticket_types: false }), ticketTypes, {}),
		null,
	)
})

test("an order minimum notes the order that reaches it", () => {
	const preview = checkoutPreview(
		values({
			minimum_requirement: "Minimum Order Amount",
			minimum_order_amounts: [{ currency: "INR", price: 10000 }],
		}),
		ticketTypes,
		{ ticketType: "vip" },
	)
	assert.equal(preview?.note, "VIP × 2 reaches the ₹10,000 minimum.")
})

test("a ticket count minimum notes that the preview uses it", () => {
	const preview = checkoutPreview(
		values({ minimum_requirement: "Minimum Ticket Count", minimum_ticket_count: 5 }),
		ticketTypes,
		{},
	)
	assert.equal(preview?.note, "Shown with the minimum of 5 tickets.")
})
