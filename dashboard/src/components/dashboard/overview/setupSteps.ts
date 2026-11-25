import type { RouteLocationRaw } from "vue-router"

import type { EventTicketTypes } from "@/types"

import type { OverviewEventDoc } from "./overviewData"

export type StepKey =
	| "dates"
	| "location"
	| "link"
	| "tickets"
	| "page"
	| "payments"
	| "questions"
	| "team"
	| "talks"

/** What the miniatures draw from: this event's own title, venue and cover. */
export interface StepEvent {
	title: string
	venue: string
	banner: string | null
}

export interface SetupStep {
	key: StepKey
	title: string
	hint: string
}

/** A step as the overview shows it: done or not, and the page that finishes it. */
export interface SetupCardStep extends SetupStep {
	done: boolean
	to: RouteLocationRaw
}

export const STEPS: SetupStep[] = [
	{ key: "dates", title: "Set dates", hint: "Start and end, or keep it TBA" },
	{ key: "location", title: "Set location", hint: "Where guests show up" },
	{ key: "link", title: "Add meeting link", hint: "Where guests join online" },
	{
		key: "tickets",
		title: "Open registrations",
		hint: "Add a ticket type, free or paid",
	},
	{
		key: "page",
		title: "Make the event page",
		hint: "A description and a cover for every share",
	},
	{
		key: "payments",
		title: "Connect payments",
		hint: "Paid tickets need a gateway to sell",
	},
]

// Nice to have, never required: only the first one not yet done is suggested.
export const OPTIONAL_STEPS: SetupStep[] = [
	{
		key: "questions",
		title: "Ask attendees questions",
		hint: "Collect details when they register",
	},
	{
		key: "team",
		title: "Invite your team",
		hint: "Co-hosts who can run this event",
	},
	{
		key: "talks",
		title: "Open a call for talks",
		hint: "Let speakers send proposals",
	},
]

/** What the steps are worked out from. */
export interface StepFacts {
	eventId: string
	doc: OverviewEventDoc
	ticketing: Pick<EventTicketTypes, "ticket_types" | "payment_providers" | "registration_form">
	hasTeam: boolean
	proposalCount: number
}

// Each step opens the page where it is finished.
const PAGES: Record<StepKey, string> = {
	dates: "event-details",
	location: "event-details",
	link: "event-details",
	page: "event-details",
	tickets: "event-registrations",
	payments: "event-payments",
	questions: "event-settings",
	team: "event-settings",
	talks: "event-talks",
}

function isDone(facts: StepFacts): Record<StepKey, boolean> {
	const { doc, ticketing } = facts
	return {
		dates: Boolean(doc.start_date),
		location: Boolean(doc.venue),
		link: Boolean(doc.meeting_link),
		tickets: ticketing.ticket_types.length > 0,
		page: Boolean(doc.banner_image && doc.about?.replace(/<[^>]+>/g, "").trim()),
		payments: ticketing.payment_providers.length > 0,
		questions: Boolean(ticketing.registration_form),
		team: facts.hasTeam,
		talks: facts.proposalCount > 0,
	}
}

// A venue for in-person events, a link for online ones; payments only once a ticket costs money.
function applies(step: SetupStep, facts: StepFacts) {
	const online = facts.doc.medium === "Online"
	if (step.key === "location") return !online
	if (step.key === "link") return online
	if (step.key === "payments")
		return facts.ticketing.ticket_types.some((type) => type.prices.some((price) => price.price > 0))
	return true
}

function routeFor(key: StepKey, facts: StepFacts): RouteLocationRaw {
	const eventId = facts.eventId
	const form = facts.ticketing.registration_form
	if (key === "questions" && form)
		return { name: "event-form", params: { eventId, formName: form } }
	return { name: PAGES[key], params: { eventId } }
}

/** The required steps that apply, then the first optional one not yet done; finished ones last. */
export function buildSteps(facts: StepFacts): SetupCardStep[] {
	const done = isDone(facts)
	const suggested = OPTIONAL_STEPS.find((step) => !done[step.key])
	return [...STEPS.filter((step) => applies(step, facts)), ...(suggested ? [suggested] : [])]
		.map((step) => ({ ...step, done: done[step.key], to: routeFor(step.key, facts) }))
		.toSorted((a, b) => Number(a.done) - Number(b.done))
}
