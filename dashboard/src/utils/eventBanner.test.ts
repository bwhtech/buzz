import assert from "node:assert/strict"
import { test } from "node:test"

import { bannerPattern } from "./eventBanner.ts"

const NAMES = ["Frappe Yatra 2026", "PyCon India", "1042", "", "a"]

test("an event always draws the same pattern", () => {
	assert.equal(bannerPattern("Frappe Yatra 2026"), bannerPattern("Frappe Yatra 2026"))
})

test("different events draw different patterns", () => {
	const patterns = new Set(NAMES.map(bannerPattern))
	assert.equal(patterns.size, NAMES.length)
})

test("ring origins stay off centre", () => {
	for (const name of NAMES) {
		const [x, y] = [...bannerPattern(name).matchAll(/at (-?\d+)% (-?\d+)%/g)][0].slice(1)
		for (const origin of [Number(x), Number(y)]) {
			assert.ok(origin <= 30 || origin >= 70, `${name} drew an origin at ${origin}%`)
			assert.ok(origin >= -10 && origin <= 110)
		}
	}
})

test("ring spacing stays inside the readable range", () => {
	for (const name of NAMES) {
		const gap = Number(bannerPattern(name).match(/transparent \d+px (\d+\.\d)px/)?.[1])
		assert.ok(gap >= 18 && gap <= 26, `${name} drew a ${gap}px gap`)
	}
})
