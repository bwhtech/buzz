import { computed, type Ref } from "vue"

import { teams } from "@/data/teams"

import { matchesText, orderEvents, parseQuery, splitOnIn, type PaletteEvent } from "./paletteQuery"
import {
	eventRows,
	searchGroups,
	sectionRows,
	type PaletteGroup,
	type PaletteRow,
	type PaletteScope,
} from "./paletteRows"
import { usePaletteCommands } from "./usePaletteCommands"
import { usePaletteSearch } from "./usePaletteSearch"

type PaletteState = {
	query: Ref<string>
	scope: Ref<PaletteScope | null>
	events: Ref<PaletteEvent[]>
	currentEventId: Ref<string | undefined>
}

/** What the palette lists for the query, the pushed scope and the event on screen. */
export function usePaletteGroups({ query, scope, events, currentEventId }: PaletteState) {
	const { commands, communityRows } = usePaletteCommands()
	const ordered = computed(() => orderEvents(events.value, currentEventId.value))
	const currentEvent = computed(() =>
		ordered.value.find((event) => event.name === currentEventId.value),
	)
	const parsed = computed(() => parseQuery(query.value, ordered.value))
	const term = computed(() => parsed.value.term)

	// A pushed chip beats `in`, which beats the page the user is on.
	const target = computed(() => ({
		event: scope.value?.event ?? parsed.value.event ?? currentEvent.value,
		source: scope.value?.source ?? parsed.value.source,
		term: term.value,
	}))
	const { groups: results } = usePaletteSearch(target)

	const resultGroups = computed(() => {
		const { event, source } = target.value
		if (!event) return []
		const groups = results.value.filter((group) => !source || group.key === source.key)
		return searchGroups(event, term.value, groups)
	})

	const filter = (rows: PaletteRow[]) =>
		rows.filter((row) => matchesText(term.value, row.label, row.keywords))

	const scopedGroups = computed<PaletteGroup[]>(() => {
		const { event, source } = scope.value as PaletteScope
		const sections = source ? [] : sectionRows(event, term.value)
		return [...resultGroups.value, { label: __("Sections"), rows: sections }]
	})

	const rootGroups = computed<PaletteGroup[]>(() => {
		const typed = Boolean(term.value)
		const event = target.value.event
		return [
			pickerGroup(),
			...resultGroups.value,
			{ label: __("Commands"), rows: filter(commands.value) },
			{ label: event ? event.title : "", rows: event ? sectionRows(event, term.value) : [] },
			{ label: __("Events"), rows: eventRows(ordered.value, term.value, teams.value.length > 1) },
			{ label: __("Communities"), rows: typed ? filter(communityRows.value) : [] },
			{ label: "", rows: hintRows() },
		]
	})

	// `harsh in dev` before the target matches: the events it could mean, to push into.
	function pickerGroup(): PaletteGroup {
		const parts = splitOnIn(query.value)
		if (!parts?.term || parsed.value.event || parsed.value.source) return { label: "", rows: [] }
		const rows = eventRows(ordered.value, parts.target, teams.value.length > 1).map((row) => ({
			...row,
			id: `pick:${row.id}`,
			keepOpen: true,
			run: () => {
				scope.value = row.scope ?? null
				query.value = parts.term
			},
		}))
		return { label: __('Search "{0}" in', [parts.term]), rows }
	}

	// Outside an event, record search needs one: offer to pick it.
	function hintRows(): PaletteRow[] {
		if (target.value.event || !term.value || !events.value.length) return []
		return [
			{
				id: "hint:in-event",
				label: __('Search "{0}" in an event…', [term.value]),
				icon: "lucide-search",
				keepOpen: true,
				run: () => (query.value = `${term.value} in `),
			},
		]
	}

	const groups = computed(() =>
		(scope.value ? scopedGroups.value : rootGroups.value).filter((group) => group.rows.length),
	)
	const rowsById = computed(
		() => new Map(groups.value.flatMap((group) => group.rows).map((row) => [row.id, row])),
	)

	return { groups, rowsById }
}
