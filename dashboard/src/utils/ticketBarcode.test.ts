import assert from "node:assert/strict"
import { test } from "node:test"
import { barcodePattern } from "./ticketBarcode.ts"

const IDS = ["a1b2c3d4e5", "0f9e8d7c6b", "1042", "a"]

test("a ticket always draws the same strip", () => {
	assert.equal(barcodePattern("a1b2c3d4e5"), barcodePattern("a1b2c3d4e5"))
})

test("different tickets draw different strips", () => {
	const strips = new Set(IDS.map((id) => barcodePattern(id)))
	assert.equal(strips.size, IDS.length)
})

test("bars and gaps stay between 1 and 3px", () => {
	for (const id of IDS) {
		for (const [, from, to] of barcodePattern(id).matchAll(/(\d+)px (\d+)px/g)) {
			const width = Number(to) - Number(from)
			assert.ok(width >= 1 && width <= 3, `${id} drew a ${width}px segment`)
		}
	}
})

test("a missing id draws nothing", () => {
	assert.equal(barcodePattern(""), "none")
})
