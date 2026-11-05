import { watchDebounced } from "@vueuse/core"
import { useCall } from "frappe-ui"
import { computed, ref, watch, type Ref } from "vue"

import { readableSources, type PaletteEvent, type SearchSource } from "./paletteQuery"

export type SearchRecord = { name: string; title: string; subtitle: string | null }
export type SearchGroup = { key: string; records: SearchRecord[] }

type SearchTarget = { event?: PaletteEvent; source?: SearchSource; term: string }
type SearchParams = { event: string; term: string; section?: string }

const MIN_TERM_LENGTH = 2
const DEBOUNCE_MS = 150

// Uncached: events and results are the session user's own.
export function usePaletteEvents() {
	return useCall<{ events: PaletteEvent[] }>({
		url: "/api/v2/method/buzz.api.search.get_palette_events",
		immediate: false,
	})
}

/** Records of one event matching the term, refetched as the user pauses typing. */
export function usePaletteSearch(target: Ref<SearchTarget>) {
	const search = useCall<{ groups: SearchGroup[] }, SearchParams>({
		url: "/api/v2/method/buzz.api.search.search_event",
		immediate: false,
	})
	const results = ref<{ event: string; groups: SearchGroup[] } | null>(null)
	const params = computed(() => searchParams(target.value))
	// Compared by value: the target object is rebuilt on every keystroke.
	const key = computed(() => JSON.stringify(params.value))
	// True from the keystroke, not the request: the debounce gap would read as "no matches".
	const pending = ref(false)
	watch(key, () => (pending.value = Boolean(params.value)))

	watchDebounced(
		key,
		async (current) => {
			const request = params.value
			if (!request) return (results.value = null)
			search.abort()
			const result = await search.submit(request).finally(() => {
				if (key.value === current) pending.value = false
			})
			// A slower, older request must not overwrite the newer query's rows.
			if (result && key.value === current)
				results.value = { event: request.event, groups: result.groups }
		},
		{ debounce: DEBOUNCE_MS },
	)

	// Earlier rows of the same event stay while the next term loads, so "No matches"
	// never flashes; another event's rows would link into the wrong one.
	const groups = computed(() =>
		params.value && results.value?.event === params.value.event ? results.value.groups : [],
	)

	return { groups, searching: pending }
}

function searchParams({ event, source, term }: SearchTarget): SearchParams | null {
	if (!event || term.length < MIN_TERM_LENGTH || !readableSources(event).length) return null
	return { event: event.name, term, ...(source ? { section: source.section } : {}) }
}
