import { firstEventPath, managerNavigation } from "@/utils/managerNavigation"

import {
	matchesText,
	sectionPath,
	SEARCH_SOURCES,
	sourceFor,
	type PaletteEvent,
	type SearchSource,
} from "./paletteQuery"
import type { SearchGroup, SearchRecord } from "./usePaletteSearch"

export type PaletteScope = { event: PaletteEvent; source?: SearchSource }

export type PaletteRow = {
	id: string
	label: string
	icon: string
	subtitle?: string
	keywords?: string[]
	to?: string
	run?: () => void
	// Picking the row keeps the palette open.
	keepOpen?: boolean
	// Tab pushes into this scope, then the query becomes `scopeQuery`.
	scope?: PaletteScope
	scopeQuery?: string
}

// `event` draws the group's label as "<event> › <label>", for results inside one event.
export type PaletteGroup = { label: string; rows: PaletteRow[]; event?: string }

const EVENT_LIMIT = 8

export function eventRows(events: PaletteEvent[], term: string, showTeam: boolean): PaletteRow[] {
	return events
		.filter((event) => matchesText(term, event.title))
		.slice(0, EVENT_LIMIT)
		.map((event) => ({
			id: `event:${event.name}`,
			label: event.title,
			icon: "lucide-box",
			subtitle: showTeam ? (event.team_title ?? undefined) : undefined,
			to: firstEventPath(event.name, event.access),
			scope: { event },
			scopeQuery: "",
		}))
}

/** The event's sidebar destinations; the searchable ones can be pushed into. */
export function sectionRows(event: PaletteEvent, term: string): PaletteRow[] {
	return managerNavigation({
		eventId: event.name,
		access: event.access,
		creatingEvent: false,
		hasSponsorships: false,
	})
		.filter((item) => matchesText(term, item.label, [event.title]))
		.map((item) => {
			const source = SEARCH_SOURCES.find((option) => item.to === sectionPath(event, option))
			return {
				id: `section:${item.to}`,
				label: `${event.title} › ${item.label}`,
				icon: item.icon,
				to: item.to,
				...(source ? { scope: { event, source }, scopeQuery: "" } : {}),
			}
		})
}

/** Per section: "harsh in Guests", opening the filtered list, then its first matches. */
export function searchGroups(
	event: PaletteEvent,
	term: string,
	groups: SearchGroup[],
): PaletteGroup[] {
	return groups.flatMap((group, index) => {
		const source = sourceFor(group.key)
		if (!source) return []
		const query = source.searchParam ? `?${source.searchParam}=${encodeURIComponent(term)}` : ""
		const header: PaletteRow = {
			id: `search:${source.key}`,
			label: `${term} in ${source.label}`,
			icon: "lucide-search",
			to: sectionPath(event, source, query),
			scope: { event, source },
			scopeQuery: term,
		}
		return [
			{
				label: source.label,
				// Once, on the first group: every group of one search shares the event.
				event: index === 0 ? event.title : undefined,
				rows: [header, ...group.records.map((record) => recordRow(event, source, record))],
			},
		]
	})
}

function recordRow(event: PaletteEvent, source: SearchSource, record: SearchRecord): PaletteRow {
	const query = source.recordParam
		? `?${source.recordParam}=${encodeURIComponent(record.name)}`
		: ""
	return {
		id: `record:${source.key}:${record.name}`,
		label: record.title,
		icon: "lucide-corner-down-right",
		subtitle: record.subtitle ?? undefined,
		to: sectionPath(event, source, query),
	}
}

export function scopeLabel(scope: PaletteScope): string {
	return scope.source ? `${scope.event.title} › ${scope.source.label}` : scope.event.title
}
