import { computed, reactive, ref, watch, type Ref } from "vue"

import {
	createVenue,
	loadVenues,
	type PlacePrediction,
	usePlaceSearch,
	venues,
} from "@/data/venues"
import { serverErrorMessage } from "@/utils/serverError"

export type LocationPicker = ReturnType<typeof useLocationPicker>

/** Search state and the two ways of adding a venue, shared by the location dialogs. */
export function useLocationPicker(team: () => string, isOpen: Ref<boolean>) {
	const query = ref("")
	const placeSearch = usePlaceSearch(query, isOpen)
	const manualError = ref("")

	watch(isOpen, (open) => {
		if (!open) return
		query.value = ""
		manualError.value = ""
	})

	const savedVenues = computed(() => {
		const text = query.value.trim().toLowerCase()
		return (venues.data ?? []).filter((row) =>
			`${row.venue_name} ${row.address ?? ""}`.toLowerCase().includes(text),
		)
	})

	async function savePlace(place: PlacePrediction) {
		const name = await placeSearch.save(place, team())
		if (name) await loadVenues(team())
		return name
	}

	async function saveManually(venue: { venue_name: string; address: string; map_link: string }) {
		manualError.value = ""
		const saved = await createVenue.submit({ team: team(), ...venue }).catch((error) => {
			manualError.value = serverErrorMessage(error)
			return null
		})
		if (!saved) return null
		await loadVenues(team())
		return saved.name
	}

	// Something is typed and nothing answers to it, so adding it by hand is the only move
	// left. Not while a list is still arriving: an empty list is not an answer yet.
	const isUnmatched = computed(
		() =>
			Boolean(query.value.trim()) &&
			!savedVenues.value.length &&
			!placeSearch.places.length &&
			!placeSearch.isSearching &&
			!(venues.loading && !venues.data),
	)

	return reactive({
		query,
		isUnmatched,
		savedVenues,
		places: computed(() => placeSearch.places),
		isSearching: computed(() => placeSearch.isSearching),
		isLoadingVenues: computed(() => venues.loading && !venues.data),
		error: computed(() => manualError.value || placeSearch.error),
		savePlace,
		saveManually,
	})
}
