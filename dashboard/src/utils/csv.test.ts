import assert from "node:assert/strict"
import { test } from "node:test"

import { csvCell, toCsv } from "./csv.ts"

test("quotes every value", () => {
	assert.equal(csvCell("Ada"), '"Ada"')
})

test("doubles an embedded quote", () => {
	assert.equal(csvCell('Ada "The Countess"'), '"Ada ""The Countess"""')
})

test("defuses a value a spreadsheet would run as a formula", () => {
	assert.equal(csvCell("=SUM(A1:A9)"), `"'=SUM(A1:A9)"`)
})

test("reads a missing value as empty", () => {
	assert.equal(csvCell(null), '""')
})

test("joins cells with commas and rows with newlines", () => {
	assert.equal(
		toCsv([
			["Name", "Email"],
			["Ada", null],
		]),
		'"Name","Email"\n"Ada",""',
	)
})
