import { refDebounced } from "@vueuse/core"
import { useCall, useDoctype, useList } from "frappe-ui"
import { computed, reactive, ref, watch, type Ref } from "vue"

import { serverErrorMessage } from "@/utils/serverError"

export interface Venue {
	name: string
	venue_name: string
	address: string
	google_place_id?: string | null
}

const team = ref("")

// Plain doctype reads and writes, so they go through the document API rather than a buzz
// endpoint. Event Venue carries the team query condition and permission hooks, so the
// team filter below narrows what the picker asks for — it is not what enforces scope.
export const venues = useList<Venue>({
	doctype: "Event Venue",
	filters: () => ({ team: team.value }),
	fields: ["name", "venue_name", "address", "google_place_id"],
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
	// One token from the first keystroke to the save, so Google bills them as a single session.
	let sessionToken = crypto.randomUUID()
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

	const venue = useCall<
		string,
		{ team: string; place_id: string; name: string; session_token: string }
	>({
		url: "/api/v2/method/buzz.api.maps.add_place_as_venue",
		method: "POST",
		immediate: false,
	})

	/** Saves the place as the team's venue and answers with the venue's `name`, or null on failure. */
	async function save(place: PlacePrediction, venueTeam: string) {
		const name = await venue
			.submit({
				team: venueTeam,
				place_id: place.place_id,
				name: place.name,
				session_token: sessionToken,
			})
			.catch(() => null)
		if (name) sessionToken = crypto.randomUUID()
		return name
	}

	return reactive({
		save,
		places: computed(() => (isSearchable.value ? (search.data ?? []) : [])),
		// Only while searching: a failed search must not leave a venue picked by hand marked as wrong.
		error: computed(() => {
			const error = search.error || venue.error
			return isOpen.value && error ? serverErrorMessage(error) : ""
		}),
	})
}
