import assert from "node:assert/strict"
import { test } from "node:test"

import { ref } from "vue"

import { useRowSelection } from "./useRowSelection.ts"

const keys = () => ref(["a", "b", "c"])

test("a key toggles into and out of the selection", () => {
	const selection = useRowSelection(keys())

	selection.toggle("b")
	assert.deepEqual(selection.selected.value, ["b"])

	selection.toggle("b")
	assert.deepEqual(selection.selected.value, [])
})

test("the selection keeps the order of the list, not the order it was picked in", () => {
	const selection = useRowSelection(keys())

	selection.toggle("c")
	selection.toggle("a")

	assert.deepEqual(selection.selected.value, ["a", "c"])
})

test("a key that stops being selectable leaves the selection", () => {
	const selectable = keys()
	const selection = useRowSelection(selectable)

	selection.select(["a", "c"])
	selectable.value = ["a", "b"]

	assert.deepEqual(selection.selected.value, ["a"])
})

test("clearing empties the selection", () => {
	const selection = useRowSelection(keys())

	selection.select(["a", "b"])
	selection.clear()

	assert.deepEqual(selection.selected.value, [])
})
