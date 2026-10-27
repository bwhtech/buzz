import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

import { conditionMatches, isRequired, isShown } from "./formLogic.ts"

// Shared with buzz/api/forms/test_conditions.py, so both evaluators agree.
const cases = JSON.parse(
	readFileSync(new URL("../../../buzz/api/forms/logic_cases.json", import.meta.url), "utf8"),
)

test("conditions match as the server matches them", () => {
	for (const { condition, values, expected } of cases.conditions) {
		assert.equal(conditionMatches(condition, values), expected, JSON.stringify(condition))
	}
})

test("rules show, hide and require as the server does", () => {
	for (const form of cases.forms) {
		for (const [fieldname, expected] of Object.entries<any>(form.questions)) {
			const question = { fieldname, mandatory: expected.mandatory }
			assert.equal(isShown(form.rules, fieldname, form.values), expected.shown, form.name)
			assert.equal(isRequired(form.rules, question, form.values), expected.required, form.name)
		}
	}
})
