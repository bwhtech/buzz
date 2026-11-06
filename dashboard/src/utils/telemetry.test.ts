import assert from "node:assert/strict"
import { test } from "node:test"

import { routePattern } from "./telemetry.ts"

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
