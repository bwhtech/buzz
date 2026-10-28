import assert from "node:assert/strict"
import { test } from "node:test"

import { blankTicketTypeValues, ticketTypeDocValues, ticketTypeError } from "./ticketTypeForm.ts"

const values = (overrides = {}) => ({
	...blankTicketTypeValues("", "INR"),
	title: "General admission",
	...overrides,
})

test("a ticket type needs a name", () => {
	assert.equal(ticketTypeError(values()), null)
	assert.equal(ticketTypeError(values({ title: " " })), "Enter a name.")
})

test("every price needs a currency and a non-negative amount", () => {
	assert.notEqual(ticketTypeError(values({ prices: [{ currency: "", price: 10 }] })), null)
	assert.notEqual(ticketTypeError(values({ prices: [{ currency: "INR", price: -1 }] })), null)
})

test("closing sales automatically needs a date", () => {
	assert.equal(ticketTypeError(values({ auto_unpublish_after: "" })), "Pick the last day to sell.")
	assert.equal(ticketTypeError(values({ auto_unpublish_after: null })), null)
})

test("the saved document trims text and stores hidden as a check", () => {
	const saved = ticketTypeDocValues(values({ title: " VIP ", is_hidden: true }))
	assert.equal(saved.title, "VIP")
	assert.equal(saved.is_hidden, 1)
})
