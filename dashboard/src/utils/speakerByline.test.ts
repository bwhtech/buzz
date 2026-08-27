import assert from "node:assert/strict"
import { test } from "node:test"

import { speakerByline } from "./speakerByline.ts"

const ME = "me@example.com"

const speaker = (first_name: string, email: string, last_name: string | null = null) => ({
	first_name,
	last_name,
	email,
})

test("no speakers have no byline", () => {
	assert.equal(speakerByline([], ME), null)
})

test("a lone speaker who is the reader is You", () => {
	assert.deepEqual(speakerByline([speaker("Me", ME)], ME), {
		lead: "You",
		rest: [],
	})
})

test("a lone speaker who is someone else gets their full name", () => {
	assert.deepEqual(speakerByline([speaker("Jane", "jane@example.com", "Doe")], ME), {
		lead: "Jane Doe",
		rest: [],
	})
})

test("a pair reads as you and the other speaker, whatever the row order", () => {
	const speakers = [speaker("Jane", "jane@example.com", "Doe"), speaker("Me", ME)]

	assert.deepEqual(speakerByline(speakers, ME), {
		lead: "You",
		rest: ["Jane Doe"],
	})
})

test("a pair without the reader keeps its row order", () => {
	const speakers = [speaker("Jane", "jane@example.com"), speaker("Ravi", "ravi@example.com")]

	assert.deepEqual(speakerByline(speakers, ME), {
		lead: "Jane",
		rest: ["Ravi"],
	})
})

test("a crowd names the reader and hides the rest", () => {
	const speakers = [
		speaker("Jane", "jane@example.com"),
		speaker("Me", ME),
		speaker("Ravi", "ravi@example.com"),
		speaker("Sam", "sam@example.com"),
	]

	assert.deepEqual(speakerByline(speakers, ME), {
		lead: "You",
		rest: ["Jane", "Ravi", "Sam"],
	})
})

test("a crowd without the reader leads with the first speaker", () => {
	const speakers = [
		speaker("Jane", "jane@example.com"),
		speaker("Ravi", "ravi@example.com"),
		speaker("Sam", "sam@example.com"),
	]

	assert.deepEqual(speakerByline(speakers, ME), {
		lead: "Jane",
		rest: ["Ravi", "Sam"],
	})
})

test("a speaker email cased differently is still the reader", () => {
	assert.deepEqual(speakerByline([speaker("Me", "Me@Example.COM")], ME), {
		lead: "You",
		rest: [],
	})
})

test("a speaker with no name falls back to their email", () => {
	assert.deepEqual(speakerByline([speaker("", "jane@example.com")], ME), {
		lead: "jane@example.com",
		rest: [],
	})
})
