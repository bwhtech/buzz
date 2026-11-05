import assert from "node:assert/strict"
import { test } from "node:test"

import { matchesText, orderEvents, parseQuery, type PaletteEvent } from "./paletteQuery.ts"

const event = (name: string, title: string): PaletteEvent => ({
	name,
	title,
	team: "T1",
	team_title: "Team",
	start_date: null,
	end_date: null,
	access: {
		details: "View",
		guests: "View",
		ticketing: null,
		talks: "View",
		sponsors: null,
		communications: null,
	},
})

const events = [event("1", "DevConf 2026"), event("2", "PyCon India")]

test("plain text stays plain", () => {
	assert.deepEqual(parseQuery("  harsh ", events), { term: "harsh" })
})

test("in <event> scopes to the matching event", () => {
	const parsed = parseQuery("harsh in pycon", events)
	assert.equal(parsed.term, "harsh")
	assert.equal(parsed.event?.name, "2")
})

test("in <section> scopes to a section, by label or keyword", () => {
	assert.equal(parseQuery("harsh in talks", events).source?.key, "talks")
	assert.equal(parseQuery("harsh in participants", events).source?.key, "guests")
})

test("the last in wins and an unknown target falls back to plain text", () => {
	assert.equal(parseQuery("ai in healthcare in devconf", events).term, "ai in healthcare")
	assert.deepEqual(parseQuery("AI in healthcare", events), { term: "AI in healthcare" })
})

test("a trailing in waits for its target", () => {
	assert.deepEqual(parseQuery("harsh in ", events), { term: "harsh" })
})

test("no events means in never scopes to one", () => {
	assert.deepEqual(parseQuery("harsh in devconf", []), { term: "harsh in devconf" })
})

test("the current event goes first", () => {
	assert.deepEqual(
		orderEvents(events, "2").map((option) => option.name),
		["2", "1"],
	)
	assert.equal(orderEvents(events, "9"), events)
})

test("text matching uses keywords and treats an empty term as a match", () => {
	assert.ok(matchesText("dark", "Switch to dark theme"))
	assert.ok(matchesText("appear", "Theme", ["appearance"]))
	assert.ok(!matchesText("zzz", "Theme"))
	assert.ok(matchesText("", "Theme"))
})
