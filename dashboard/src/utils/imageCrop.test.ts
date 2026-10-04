import assert from "node:assert/strict"
import { test } from "node:test"

import { clampOffset, coverScale, rotatedSize } from "./imageCrop.ts"

test("a half turn leaves the footprint alone", () => {
	assert.deepEqual(rotatedSize({ width: 400, height: 300 }, 180), { width: 400, height: 300 })
})

test("a quarter turn swaps the axes", () => {
	assert.deepEqual(rotatedSize({ width: 400, height: 300 }, 90), { width: 300, height: 400 })
})

test("a negative quarter turn swaps them the same way", () => {
	assert.deepEqual(rotatedSize({ width: 400, height: 300 }, -90), { width: 300, height: 400 })
})

test("a landscape image covering a 3:1 frame is scaled by its width", () => {
	// 600x400 into 300x100: fitting the height would need 0.25 and leave the width short.
	assert.equal(coverScale({ width: 600, height: 400 }, { width: 300, height: 100 }), 0.5)
})

test("a wide image covering a square frame is scaled by its height", () => {
	assert.equal(coverScale({ width: 800, height: 200 }, { width: 300, height: 300 }), 1.5)
})

test("an image with no dimensions yet falls back to unscaled", () => {
	assert.equal(coverScale({ width: 0, height: 0 }, { width: 300, height: 100 }), 1)
})

test("a pan inside the overflow is left where it was put", () => {
	const frame = { width: 300, height: 100 }
	const rendered = { width: 500, height: 300 }
	assert.deepEqual(clampOffset({ x: 40, y: -30 }, rendered, frame), { x: 40, y: -30 })
})

test("a pan past an edge stops at half the overflow", () => {
	const frame = { width: 300, height: 100 }
	const rendered = { width: 500, height: 300 }
	assert.deepEqual(clampOffset({ x: 999, y: -999 }, rendered, frame), { x: 100, y: -100 })
})

test("an image no bigger than its frame cannot be panned", () => {
	const frame = { width: 300, height: 100 }
	assert.deepEqual(clampOffset({ x: 50, y: 50 }, { width: 300, height: 100 }, frame), {
		x: 0,
		y: 0,
	})
})
