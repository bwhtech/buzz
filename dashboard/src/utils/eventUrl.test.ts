import assert from "node:assert/strict"
import { test } from "node:test"

import { eventUrl } from "./eventUrl.ts"

const withOrigin = (origin: string, run: () => void) => {
	// The helper reads the live location; there is no browser under node --test.
	;(globalThis as { window?: unknown }).window = { location: { origin } }
	try {
		run()
	} finally {
		;(globalThis as { window?: unknown }).window = undefined
	}
}

test("hangs the route off the current origin", () => {
	withOrigin("https://buzz.example.com", () => {
		assert.equal(eventUrl("frappeverse-2026"), "https://buzz.example.com/frappeverse-2026")
	})
})

test("keeps the port, which differs between the dashboard and the bench", () => {
	withOrigin("http://buzz.localhost:8080", () => {
		assert.equal(eventUrl("summit"), "http://buzz.localhost:8080/summit")
	})
})
