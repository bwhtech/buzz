import assert from "node:assert/strict"
import { test } from "node:test"

import type { CouponTicketType } from "@/types"

import {
	blankCouponValues,
	cleanPromoCode,
	couponCurrencies,
	couponDocValues,
	couponValuesOf,
	eligibleTicketTypes,
	couponError,
	isCouponValid,
} from "./couponForm.ts"

const ticketTypes: CouponTicketType[] = [
	{ name: "free", title: "Normal", prices: [{ currency: "INR", price: 0 }] },
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

const promo = (overrides = {}) => ({
	...blankCouponValues(),
	code: "EARLYBIRD",
	discount_percentage: 20,
	...overrides,
})

test("free ticket types are never eligible", () => {
	assert.deepEqual(
		eligibleTicketTypes(promo(), ticketTypes).map((row) => row.name),
		["student", "vip"],
	)
})

test("specific scope keeps only the picked ticket types", () => {
	const values = promo({ applies_to_all_ticket_types: false, ticket_types: ["student"] })
	assert.deepEqual(
		eligibleTicketTypes(values, ticketTypes).map((row) => row.name),
		["student"],
	)
})

test("currencies come from the eligible ticket types", () => {
	assert.deepEqual(couponCurrencies(promo(), ticketTypes), ["INR", "USD"])
	const values = promo({ applies_to_all_ticket_types: false, ticket_types: ["student"] })
	assert.deepEqual(couponCurrencies(values, ticketTypes), ["INR"])
})

test("a promo code needs a code and a discount", () => {
	assert.equal(isCouponValid(promo(), ticketTypes), true)
	assert.equal(isCouponValid(promo({ code: " " }), ticketTypes), false)
	assert.equal(isCouponValid(promo({ discount_percentage: 0 }), ticketTypes), false)
	assert.equal(isCouponValid(promo({ discount_percentage: 120 }), ticketTypes), false)
})

test("a fixed amount needs an amount in every currency", () => {
	const inrOnly = promo({
		discount_type: "Flat Amount",
		discount_amounts: [{ currency: "INR", price: 250 }],
	})
	assert.equal(isCouponValid(inrOnly, ticketTypes), false)
	const both = {
		...inrOnly,
		discount_amounts: [...inrOnly.discount_amounts, { currency: "USD", price: 3 }],
	}
	assert.equal(isCouponValid(both, ticketTypes), true)
})

test("a specific scope needs at least one ticket type", () => {
	assert.equal(isCouponValid(promo({ applies_to_all_ticket_types: false }), ticketTypes), false)
})

test("a minimum ticket count must be positive", () => {
	const values = promo({ minimum_requirement: "Minimum Ticket Count", minimum_ticket_count: 0 })
	assert.equal(isCouponValid(values, ticketTypes), false)
})

test("the saved document drops amounts for currencies no longer sold", () => {
	const values = promo({
		code: " earlybird ",
		applies_to_all_ticket_types: false,
		ticket_types: ["student"],
		discount_type: "Flat Amount",
		discount_amounts: [
			{ currency: "INR", price: 250 },
			{ currency: "USD", price: 3 },
		],
	})
	const doc = couponDocValues(values, ticketTypes)
	assert.equal(doc.code, "EARLYBIRD")
	assert.deepEqual(doc.discount_amounts, [{ currency: "INR", price: 250 }])
	assert.deepEqual(doc.ticket_types, [{ ticket_type: "student" }])
})

test("an automatic coupon keeps its name as typed", () => {
	const doc = couponDocValues(
		promo({ coupon_type: "Automatic", code: " Group of 5+ " }),
		ticketTypes,
	)
	assert.equal(doc.code, "Group of 5+")
})

test("an automatic coupon needs a name", () => {
	assert.equal(isCouponValid(promo({ coupon_type: "Automatic", code: "" }), ticketTypes), false)
	assert.equal(
		isCouponValid(promo({ coupon_type: "Automatic", code: "Group of 5+" }), ticketTypes),
		true,
	)
})

test("a coupon can't start after it ends", () => {
	const values = promo({ starts_on: "2026-12-10", expires_on: "2026-12-01" })
	assert.equal(isCouponValid(values, ticketTypes), false)
})

test("a cleared date saves as no date", () => {
	assert.equal(
		couponDocValues(promo({ starts_on: "", expires_on: "" }), ticketTypes).expires_on,
		null,
	)
})

test("values copy from a reactive coupon", async () => {
	const { reactive } = await import("vue")
	const coupon = reactive({
		...blankCouponValues(),
		name: "c1",
		enabled: true,
		times_used: 0,
		status: "Active" as const,
		discount_amounts: [{ currency: "INR", price: 250 }],
	})
	assert.deepEqual(couponValuesOf(coupon).discount_amounts, [{ currency: "INR", price: 250 }])
})

test("a promo code drops spaces and symbols as it is typed", () => {
	assert.equal(cleanPromoCode("early bird 20%!"), "EARLYBIRD20")
	assert.equal(cleanPromoCode("save-20_now"), "SAVE-20_NOW")
})

test("a promo code with a space is invalid, an automatic name with one is fine", () => {
	assert.equal(isCouponValid(promo({ code: "EARLY BIRD" }), ticketTypes), false)
	assert.equal(
		isCouponValid(promo({ coupon_type: "Automatic", code: "Group of 5+" }), ticketTypes),
		true,
	)
})

test("an access code without hidden ticket types says why it can't save", () => {
	const values = promo({ coupon_type: "Access Code", discount_type: "None" })
	assert.equal(couponError(values, ticketTypes), "Pick at least one hidden ticket type to unlock.")
	assert.equal(couponError({ ...values, ticket_types: [ticketTypes[0].name] }, ticketTypes), null)
})

test("a blank access code starts without a discount", () => {
	assert.equal(blankCouponValues("Access Code").discount_type, "None")
	assert.equal(blankCouponValues().discount_type, "Percentage")
})
