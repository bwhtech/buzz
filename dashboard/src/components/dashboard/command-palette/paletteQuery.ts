import type { EventAccess, EventSection } from "@/types"

export type PaletteEvent = {
	name: string
	title: string
	team: string | null
	team_title: string | null
	start_date: string | null
	end_date: string | null
	access: EventAccess
}

export type SourceKey = "guests" | "talks" | "sponsors" | "coupons" | "schedule" | "communications"

export type SearchSource = {
	key: SourceKey
	label: string
	section: EventSection
	path: string
	// The page's own list search, filled from the palette's term.
	searchParam?: string
	// Opens one record in the page's drawer.
	recordParam?: string
	keywords?: string[]
}

export const SEARCH_SOURCES: SearchSource[] = [
	{
		key: "guests",
		label: "Guests",
		section: "guests",
		path: "guests",
		searchParam: "q",
		recordParam: "guest",
		keywords: ["participants", "attendees", "tickets"],
	},
	{
		key: "talks",
		label: "Talks",
		section: "talks",
		path: "talks",
		searchParam: "q",
		recordParam: "proposal",
		keywords: ["proposals", "speakers"],
	},
	{
		key: "sponsors",
		label: "Sponsors",
		section: "sponsors",
		path: "sponsorships",
		searchParam: "sponsor_q",
		recordParam: "sponsor",
		keywords: ["sponsorships"],
	},
	{
		key: "coupons",
		label: "Coupons",
		section: "ticketing",
		path: "coupons",
		recordParam: "coupon",
	},
	{ key: "schedule", label: "Schedule", section: "talks", path: "schedule" },
	{
		key: "communications",
		label: "Announcements",
		section: "communications",
		path: "communications",
		recordParam: "communication",
		keywords: ["communications", "emails"],
	},
]

export type ParsedQuery = { term: string; event?: PaletteEvent; source?: SearchSource }

/** `harsh in devconf` or `harsh in talks`; anything else is plain text. */
export function parseQuery(query: string, events: PaletteEvent[]): ParsedQuery {
	const parts = splitOnIn(query)
	if (!parts) return { term: query.trim() }

	const { term, target } = parts
	if (!target) return { term }

	const source = SEARCH_SOURCES.find((option) => matchesSource(option, target))
	if (source) return { term, source }
	const event = events.find((option) => option.title.toLowerCase().includes(target))
	return event ? { term, event } : { term: query.trim() }
}

/** The text before and after the last ` in `, the target lowercased. */
export function splitOnIn(query: string): { term: string; target: string } | null {
	const at = query.toLowerCase().lastIndexOf(" in ")
	if (at < 0) return null
	return {
		term: query.slice(0, at).trim(),
		target: query
			.slice(at + 4)
			.trim()
			.toLowerCase(),
	}
}

function matchesSource(source: SearchSource, target: string): boolean {
	return [source.label, ...(source.keywords ?? [])].some((word) =>
		word.toLowerCase().startsWith(target),
	)
}

export function matchesText(term: string, text: string, keywords: string[] = []): boolean {
	const needle = term.trim().toLowerCase()
	return !needle || [text, ...keywords].some((word) => word.toLowerCase().includes(needle))
}

/** The server orders upcoming then past; the event on screen goes first. */
export function orderEvents(events: PaletteEvent[], currentId?: string): PaletteEvent[] {
	const current = events.find((event) => event.name === currentId)
	return current ? [current, ...events.filter((event) => event !== current)] : events
}

export function readableSources(event: PaletteEvent): SearchSource[] {
	return SEARCH_SOURCES.filter((source) => event.access[source.section])
}

export function sourceFor(key: string): SearchSource | undefined {
	return SEARCH_SOURCES.find((source) => source.key === key)
}

export function sectionPath(event: PaletteEvent, source: SearchSource, query = ""): string {
	return `/manage/events/${event.name}/${source.path}${query}`
}
