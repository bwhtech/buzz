import assert from "node:assert/strict"
import { test } from "node:test"

import type { EventTicketTypes, RegistrationRequest } from "../types.ts"
import {
	freedSeats,
	isQueueEnabled,
	matchesTicketType,
	nextInLine,
	shortAge,
	sortRequests,
} from "./requestQueue.ts"

let counter = 0
const waiting = (ticketType: string, position: number | null, amount = 0): RegistrationRequest => ({
	name: `B-${++counter}`,
	status: position === null ? "Rejected" : "Waitlisted",
	request_type: "Waitlist",
	docstatus: 0,
	position,
	offer_expires_at: null,
	buyer_name: `Person ${counter}`,
	buyer_email: null,
	total_amount: amount,
	currency: "INR",
	requested_at: `2026-11-01 10:00:0${counter % 10}`,
	attendees: [{ full_name: "", email: null, ticket_type: ticketType }],
	answers: [],
})

test("let in next n takes the front of that ticket type's line", () => {
	const third = waiting("General", 3)
	const first = waiting("General", 1)
	const student = waiting("Student", 1)
	const second = waiting("General", 2)
	const removed = waiting("General", null)
	const rows = [third, first, student, second, removed]
	assert.deepEqual(nextInLine(rows, "General", 2), [first, second])
	assert.deepEqual(nextInLine(rows, "General", 0), [])
})

test("freed seats cap at the people waiting and skip ticket types with none", () => {
	const rows = [waiting("General", 1), waiting("General", 2), waiting("Student", 1)]
	const freed = freedSeats({ General: 5, Student: 1, Workshop: 3 }, rows)
	assert.deepEqual(
		freed.map((entry) => [entry.ticketType, entry.people.length]),
		[
			["General", 2],
			["Student", 1],
		],
	)
})

test("oldest first keeps queue order, name sorts alphabetically", () => {
	const [first, second, third] = [
		"2026-11-01 10:00:01",
		"2026-11-01 10:00:02",
		"2026-11-01 10:00:03",
	].map((requested_at, index) => ({
		...waiting("General", index + 1),
		requested_at,
		buyer_name: `Person ${index}`,
	}))
	assert.deepEqual(sortRequests([third, first, second], "oldest"), [first, second, third])
	assert.deepEqual(sortRequests([third, first, second], "newest"), [third, second, first])
	assert.deepEqual(sortRequests([third, first, second], "name"), [first, second, third])
})

test("ticket type filter matches one type, empty means all", () => {
	const row = waiting("General", 1)
	assert.equal(matchesTicketType(row, "General"), true)
	assert.equal(matchesTicketType(row, "Student"), false)
	assert.equal(matchesTicketType(row, ""), true)
})

const settings = (overrides: Partial<EventTicketTypes>, ticketTypes: object[] = []) =>
	({
		requires_approval: false,
		enable_waitlist: false,
		...overrides,
		ticket_types: ticketTypes,
	}) as EventTicketTypes

test("approval is enabled by the event flag or any ticket type", () => {
	assert.equal(isQueueEnabled("Approval", settings({})), false)
	assert.equal(isQueueEnabled("Approval", settings({ requires_approval: true })), true)
	assert.equal(isQueueEnabled("Approval", settings({}, [{ requires_approval: true }])), true)
})

test("waitlist is enabled by the event flag or a ticket type with a seat limit", () => {
	assert.equal(isQueueEnabled("Waitlist", settings({})), false)
	assert.equal(isQueueEnabled("Waitlist", settings({ enable_waitlist: true })), true)
	const unlimited = [{ enable_waitlist: true, max_tickets_available: 0 }]
	assert.equal(isQueueEnabled("Waitlist", settings({}, unlimited)), false)
	assert.equal(
		isQueueEnabled(
			"Waitlist",
			settings({}, [{ enable_waitlist: true, max_tickets_available: 50 }]),
		),
		true,
	)
})

test("ages read in minutes, hours, then days", () => {
	assert.deepEqual(
		[shortAge(0), shortAge(59), shortAge(90), shortAge(60 * 49)],
		["1m", "59m", "2h", "2d"],
	)
})
