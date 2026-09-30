import { refDebounced } from "@vueuse/core"
import { useCall, useDoctype, useList } from "frappe-ui"
import { computed, reactive, ref, watch, type Ref } from "vue"

import { serverErrorMessage } from "@/utils/serverError"

export interface Venue {
	name: string
	venue_name: string
	address: string
}

const team = ref("")

// Plain doctype reads and writes, so they go through the document API rather than a buzz
// endpoint. Event Venue carries the team query condition and permission hooks, so the
// team filter below narrows what the picker asks for — it is not what enforces scope.
export const venues = useList<Venue>({
	doctype: "Event Venue",
	filters: () => ({ team: team.value }),
	fields: ["name", "venue_name", "address"],
	orderBy: "modified desc",
	// One page holds every venue a team has; the picker does not page.
	limit: 1000,
	immediate: false,
	refetch: false,
})

export function loadVenues(name: string) {
	team.value = name
	return venues.reload()
}

// The server names the venue, so the insert answers with the `name` to select.
export const createVenue = useDoctype<Venue & { team: string }>("Event Venue").insert

export interface PlacePrediction {
	place_id: string
	name: string
	address: string | null
}

const MINIMUM_PLACE_QUERY_LENGTH = 3

/** Google Maps places for what is typed into an open picker, on a site with place search set up. */
export function usePlaceSearch(query: Ref<string>, isOpen: Ref<boolean>) {
	const debouncedQuery = refDebounced(query, 300)
	// One token for the whole search, so Google bills its keystrokes as a single session.
	const sessionToken = crypto.randomUUID()
	const search = useCall<PlacePrediction[], { query: string; session_token: string }>({
		url: "/api/v2/method/buzz.api.maps.search_places",
		immediate: false,
	})

	const text = computed(() => debouncedQuery.value.trim())
	const isSearchable = computed(
		() =>
			Boolean(window.google_place_search_enabled) &&
			text.value.length >= MINIMUM_PLACE_QUERY_LENGTH,
	)

	// A closed picker's query is the chosen venue's label, not something to search for.
	watch(text, () => {
		if (!isSearchable.value || !isOpen.value) return
		// The failure is kept on `search.error`, which `error` below reads.
		search.submit({ query: text.value, session_token: sessionToken }).catch(() => {})
	})

	return reactive({
		places: computed(() => (isSearchable.value ? (search.data ?? []) : [])),
		// Only while searching: a failed search must not leave a venue picked by hand marked as wrong.
		error: computed(() => (isOpen.value && search.error ? serverErrorMessage(search.error) : "")),
	})
}
