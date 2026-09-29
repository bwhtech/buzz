import assert from "node:assert/strict"
import { test } from "node:test"

import { DEFAULT_PULSE_CLIENT_URL, routePattern, trustedClientUrl } from "./telemetry.ts"

test("a missing client url falls back to the pulse cdn", () => {
	assert.equal(trustedClientUrl(undefined, "https://pulse.example"), DEFAULT_PULSE_CLIENT_URL)
})

test("a client url on the ingest host is trusted", () => {
	const url = "https://pulse.example/assets/pulse/js/pulse_client.js"
	assert.equal(trustedClientUrl(url, "https://pulse.example"), url)
})

test("a client url on the pulse cdn is trusted", () => {
	assert.equal(
		trustedClientUrl(DEFAULT_PULSE_CLIENT_URL, "https://pulse.example"),
		DEFAULT_PULSE_CLIENT_URL,
	)
})

test("a client url on another origin falls back to the pulse cdn", () => {
	assert.equal(
		trustedClientUrl("https://attacker.example/pulse_client.js", "https://pulse.example"),
		DEFAULT_PULSE_CLIENT_URL,
	)
})

test("a plain http client url falls back to the pulse cdn", () => {
	assert.equal(
		trustedClientUrl(
			"http://pulse.example/assets/pulse/js/pulse_client.js",
			"http://pulse.example",
		),
		DEFAULT_PULSE_CLIENT_URL,
	)
})

test("a malformed host does not throw", () => {
	assert.equal(
		trustedClientUrl("https://pulse.example/client.js", "not a url"),
		DEFAULT_PULSE_CLIENT_URL,
	)
})

test("the route pattern replaces real ids", () => {
	const route = {
		path: "/account/tickets/TICKET-123",
		matched: [{ path: "/account" }, { path: "/account/tickets/:ticketId" }],
	} as unknown as Parameters<typeof routePattern>[0]
	assert.equal(routePattern(route), "/account/tickets/:ticketId")
})

test("an unmatched route falls back to its path", () => {
	const route = { path: "/unknown", matched: [] } as unknown as Parameters<typeof routePattern>[0]
	assert.equal(routePattern(route), "/unknown")
})
