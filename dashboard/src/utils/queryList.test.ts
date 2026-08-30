import assert from "node:assert/strict"
import { test } from "node:test"

import { formatQueryList, parseQueryList } from "./queryList.ts"

test("a missing or blank param is no selection", () => {
	assert.deepEqual(parseQueryList(null), [])
	assert.deepEqual(parseQueryList(undefined), [])
	assert.deepEqual(parseQueryList(""), [])
	assert.deepEqual(parseQueryList(",,"), [])
})

test("values round-trip through the comma form", () => {
	assert.deepEqual(parseQueryList("hosting,attending"), ["hosting", "attending"])
	assert.equal(formatQueryList(["hosting", "attending"]), "hosting,attending")
})

test("padding a hand-edited URL picked up is dropped", () => {
	assert.deepEqual(parseQueryList("hosting, attending"), ["hosting", "attending"])
})

test("an empty selection formats to null, so the param can be removed", () => {
	assert.equal(formatQueryList([]), null)
	assert.equal(formatQueryList(["", "  "]), null)
})
