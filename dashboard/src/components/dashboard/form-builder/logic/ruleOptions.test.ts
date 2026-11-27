import assert from "node:assert/strict"
import { test } from "node:test"

import type { DoctypeField } from "../useFormBuilder.ts"
import { ruleFields } from "./ruleOptions.ts"

const link = (fieldname: string, options: string, linkOptions: DoctypeField["link_options"]) => ({
	fieldname,
	fieldtype: "Link",
	label: fieldname,
	options,
	link_options: linkOptions,
	offered: true,
	locked: false,
})

const fieldnames = (fields: DoctypeField[]) =>
	ruleFields(fields, [], 0).map((field) => field.fieldname)

test("a link with choices can be tested", () => {
	const ticketType = link("ticket_type", "Event Ticket Type", [{ value: "VIP", label: "VIP" }])
	assert.deepEqual(fieldnames([ticketType]), ["ticket_type"])
})

test("a link with no choices is left out", () => {
	assert.deepEqual(fieldnames([link("host", "Event Host", null)]), [])
	assert.deepEqual(fieldnames([link("host", "Event Host", [])]), [])
})
