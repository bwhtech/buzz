import assert from "node:assert/strict"
import { test } from "node:test"
import { DEFAULT_DIAL_CODE, formatPhone, parsePhone } from "./phone.ts"

const KNOWN = ["+1", "+91", "+44", "+971"]

test("default dial code is +91", () => {
	assert.equal(DEFAULT_DIAL_CODE, "+91")
})

test("formatPhone uses Frappe's hyphen format", () => {
	assert.equal(formatPhone("+1", "5551234567"), "+1-5551234567")
})

test("formatPhone strips non-digits from the number", () => {
	assert.equal(formatPhone("+91", "(900) 009-0000"), "+91-9000090000")
})

test("formatPhone returns empty string with no digits", () => {
	assert.equal(formatPhone("+1", ""), "")
})

test("parses the canonical hyphen format", () => {
	assert.deepEqual(parsePhone("+91-9000090000", KNOWN), {
		dialCode: "+91",
		localNumber: "9000090000",
	})
})

test("parses a legacy space-separated value", () => {
	assert.deepEqual(parsePhone("+91 9000090000", KNOWN), {
		dialCode: "+91",
		localNumber: "9000090000",
	})
})

test("parses a no-space value using the known list (not greedy)", () => {
	assert.deepEqual(parsePhone("+919000090000", KNOWN), {
		dialCode: "+91",
		localNumber: "9000090000",
	})
})

test("strips a doubled dial code", () => {
	assert.deepEqual(parsePhone("+91 +91 9000090000", KNOWN), {
		dialCode: "+91",
		localNumber: "9000090000",
	})
})

test("empty input yields no code and empty number", () => {
	assert.deepEqual(parsePhone("", KNOWN), { dialCode: null, localNumber: "" })
	assert.deepEqual(parsePhone(null, KNOWN), { dialCode: null, localNumber: "" })
})

test("bare local number keeps no dial code", () => {
	assert.deepEqual(parsePhone("9000090000", KNOWN), {
		dialCode: null,
		localNumber: "9000090000",
	})
})

test("fallback parse works when known list is empty", () => {
	assert.deepEqual(parsePhone("+91-9000090000", []), {
		dialCode: "+91",
		localNumber: "9000090000",
	})
})

test("parse -> format normalizes legacy space to hyphen", () => {
	const { dialCode, localNumber } = parsePhone("+91 9000090000", KNOWN)
	assert.equal(formatPhone(dialCode, localNumber), "+91-9000090000")
})

test("parse -> format self-heals a doubled value", () => {
	const { dialCode, localNumber } = parsePhone("+91 +91 9000090000", KNOWN)
	assert.equal(formatPhone(dialCode, localNumber), "+91-9000090000")
})

test("parse -> format is idempotent for the canonical value", () => {
	const { dialCode, localNumber } = parsePhone("+91-9000090000", KNOWN)
	assert.equal(formatPhone(dialCode, localNumber), "+91-9000090000")
})
