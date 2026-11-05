import { watchDebounced } from "@vueuse/core"
import { useCall } from "frappe-ui"
import { computed, ref, type Ref } from "vue"

import { readableSources, type PaletteEvent, type SearchSource } from "./paletteQuery"

export type SearchRecord = { name: string; title: string; subtitle: string | null }
export type SearchGroup = { key: string; section: string; records: SearchRecord[] }

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
	const groups = ref<SearchGroup[]>([])
	const params = computed(() => searchParams(target.value))
	// Compared by value: the target object is rebuilt on every keystroke.
	const key = computed(() => JSON.stringify(params.value))

	watchDebounced(
		key,
		async (current) => {
			groups.value = []
			if (!params.value) return
			search.abort()
			const result = await search.submit(params.value)
			// A slower, older request must not overwrite the newer query's rows.
			if (result && key.value === current) groups.value = result.groups
		},
		{ debounce: DEBOUNCE_MS },
	)

	return { groups, loading: computed(() => search.loading) }
}

function searchParams({ event, source, term }: SearchTarget): SearchParams | null {
	if (!event || term.length < MIN_TERM_LENGTH || !readableSources(event).length) return null
	return { event: event.name, term, ...(source ? { section: source.section } : {}) }
}
