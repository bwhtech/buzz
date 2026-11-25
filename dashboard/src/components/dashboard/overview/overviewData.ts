import { dayjs, useDoc, useList } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc, useRegistrationTrend } from "@/data/events"
import { useProposalTrend } from "@/data/proposals"
import { useEventTicketTypes } from "@/data/ticketTypes"

import { buildMetrics } from "./overviewMetrics"
import { buildSteps, type StepFacts } from "./setupSteps"

export interface EventSummary {
	title: string
	dateLabel: string
	timeLabel: string
	startDate: string | null
	venue: string
	venueDetail: string
	venueMissing: boolean
	banner: string | null
	route: string
	teamId: string
	teamName: string
	teamLogo: string | undefined
	isPublished: boolean
}

export type OverviewEventDoc = {
	title: string
	team: string | null
	route: string | null
	start_date?: string | null
	start_time?: string | null
	time_zone?: string | null
	venue?: string | null
	medium?: string | null
	meeting_link?: string | null
	banner_image?: string | null
	about?: string | null
	is_published: 0 | 1
}

type VenueDoc = { name: string; venue_name: string; city: string | null; address: string | null }
type TeamDoc = { name: string; team_name: string; logo: string | null }

// A call that fails (no access to that section) counts as settled with nothing to show.
const settled = (call: { data: unknown; error: unknown }) => Boolean(call.data || call.error)

const NO_TICKETING: StepFacts["ticketing"] = {
	ticket_types: [],
	payment_providers: [],
	registration_form: null,
}

/** Everything the overview reads: the event, its setup state and its numbers. */
export function useEventOverview(eventId: string) {
	const event = useEventDoc(() => eventId)
	const doc = computed(() => event.doc as unknown as OverviewEventDoc | null)
	const team = useDoc<TeamDoc>({ doctype: "Buzz Team", name: () => doc.value?.team || "" })
	const venue = useDoc<VenueDoc>({ doctype: "Event Venue", name: () => doc.value?.venue || "" })
	const ticketing = useEventTicketTypes(eventId)
	const collaborators = useList<{ name: string }>({
		doctype: "Buzz Event Collaborator",
		filters: { event: eventId },
		fields: ["name"],
		limit: 1,
	})
	const registrations = useRegistrationTrend(eventId)
	const proposals = useProposalTrend(eventId)

	// Without access to ticketing the steps still show, with no tickets or form known.
	const facts = computed<StepFacts | null>(() =>
		doc.value && settled(ticketing)
			? {
					eventId,
					doc: doc.value,
					ticketing: ticketing.data ?? NO_TICKETING,
					hasTeam: Boolean(collaborators.data?.length),
					proposalCount: proposals.data?.total ?? 0,
				}
			: null,
	)
	const steps = computed(() => (facts.value ? buildSteps(facts.value) : []))
	const summary = computed(() => summarise(doc.value, team.doc, venue.doc))
	const metrics = computed(() => buildMetrics(registrations.data, proposals.data, ticketing.data))
	const metricsLoaded = computed(() => settled(registrations) && settled(proposals))
	return { summary, steps, metrics, metricsLoaded }
}

function summarise(
	doc: OverviewEventDoc | null,
	team: TeamDoc | null,
	venue: VenueDoc | null,
): EventSummary {
	return {
		title: doc?.title || "",
		...dateLabels(doc),
		...venueLabels(doc, venue),
		banner: doc?.banner_image || null,
		route: doc?.route || "",
		teamId: doc?.team || "",
		teamName: team?.team_name || "",
		teamLogo: team?.logo || undefined,
		isPublished: Boolean(doc?.is_published),
	}
}

function dateLabels(doc: OverviewEventDoc | null) {
	if (!doc?.start_date)
		return {
			startDate: null,
			dateLabel: "Date to be announced",
			timeLabel: "Add a date to show the time",
		}
	const time = doc.start_time
		? `${dayjs(`2000-01-01 ${doc.start_time}`).format("h:mm A")} ${doc.time_zone || ""}`.trim()
		: "Time to be announced"
	return {
		startDate: doc.start_date,
		dateLabel: dayjs(doc.start_date).format("dddd, D MMMM"),
		timeLabel: time,
	}
}

function venueLabels(doc: OverviewEventDoc | null, venue: VenueDoc | null) {
	if (doc?.medium === "Online")
		return doc.meeting_link
			? { venue: "Online", venueDetail: "Link shared with guests", venueMissing: false }
			: { venue: "Online", venueDetail: "Meeting link missing", venueMissing: true }
	if (doc?.venue)
		return {
			venue: venue?.venue_name || doc.venue,
			venueDetail: venue?.city || venue?.address || "",
			venueMissing: false,
		}
	return {
		venue: "Location missing",
		venueDetail: "Guests won't know where to go",
		venueMissing: true,
	}
}
