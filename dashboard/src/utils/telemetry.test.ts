import assert from "node:assert/strict"
import { test } from "node:test"

import { routePattern } from "./telemetry.ts"

test("the route pattern replaces real ids", () => {
	const route = {
		path: "/manage/events/EVENT-123/guests",
		matched: [{ path: "/manage" }, { path: "/manage/events/:eventId/guests" }],
	} as unknown as Parameters<typeof routePattern>[0]
	assert.equal(routePattern(route), "/manage/events/:eventId/guests")
})

test("an unmatched route falls back to its path", () => {
	const route = { path: "/unknown", matched: [] } as unknown as Parameters<typeof routePattern>[0]
	assert.equal(routePattern(route), "/unknown")
})
