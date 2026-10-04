import assert from "node:assert/strict"
import { test } from "node:test"

import { hostOf, isValidUrl, linkIconClass, normalizeUrl } from "./eventLinks.ts"

test("adds https to a bare address", () => {
	assert.equal(normalizeUrl(" lu.ma/pune "), "https://lu.ma/pune")
	assert.equal(normalizeUrl("http://example.com"), "http://example.com")
})

test("accepts web addresses and refuses everything else", () => {
	assert.ok(isValidUrl("example.com/page"))
	assert.ok(isValidUrl("https://t.me/frappepune"))
	assert.ok(!isValidUrl(""))
	assert.ok(!isValidUrl("not a url"))
	assert.ok(!isValidUrl("localhost"))
})

test("shows the host without www", () => {
	assert.equal(hostOf("https://www.github.com/frappe"), "github.com")
})

test("draws an unknown or missing icon as a link", () => {
	assert.equal(linkIconClass("map-pin"), "lucide-map-pin")
	assert.equal(linkIconClass(null), "lucide-link")
	assert.equal(linkIconClass("github"), "lucide-link")
})
