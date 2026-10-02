import assert from "node:assert/strict"
import { test } from "node:test"

import { resolveLoginRedirect } from "./loginRedirect.ts"

const ORIGIN = "https://buzz.events"

test("keeps a same-origin path with its query", () => {
	assert.equal(resolveLoginRedirect("/events?category=meetups", ORIGIN), "/events?category=meetups")
})

test("strips the origin off a same-origin absolute URL", () => {
	assert.equal(resolveLoginRedirect("https://buzz.events/events/scipy", ORIGIN), "/events/scipy")
})

test("falls back to the dashboard for another origin", () => {
	assert.equal(resolveLoginRedirect("https://evil.example/phish", ORIGIN), "/b")
	assert.equal(resolveLoginRedirect("//evil.example/phish", ORIGIN), "/b")
})

test("falls back to the dashboard when missing", () => {
	assert.equal(resolveLoginRedirect(undefined, ORIGIN), "/b")
	assert.equal(resolveLoginRedirect("", ORIGIN), "/b")
	assert.equal(resolveLoginRedirect(["/a", "/b"], ORIGIN), "/b")
})

test("drops a javascript: URL", () => {
	assert.equal(resolveLoginRedirect("javascript:alert(1)", ORIGIN), "/b")
})
