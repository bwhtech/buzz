import { computed, reactive, ref } from "vue"

import type { LocationPicker } from "@/components/dashboard/events/location/useLocationPicker"
import { type PlacePrediction, type Venue, useAddressLocation, venues } from "@/data/venues"

export type LocationSelection = ReturnType<typeof useLocationSelection>

/** What the location dialog has picked: one place, or several in order for a group venue. */
export function useLocationSelection(picker: LocationPicker) {
	const isMultiple = ref(false)
	const selected = ref<string[]>([])
	const active = ref<Venue | null>(null)
	const activePlace = ref<PlacePrediction | null>(null)
	const hovered = ref<string | null>(null)
	const isSaving = ref(false)
	const addressLocation = useAddressLocation()
	// A Google Maps place is not a venue yet, so it gets its pin from its address.
	const placePin = ref<Venue | null>(null)

	const byName = computed(() => new Map((venues.data ?? []).map((venue) => [venue.name, venue])))
	const chosen = computed(() => selected.value.flatMap((name) => byName.value.get(name) ?? []))
	const places = computed(() => [
		...(venues.data ?? []).filter((venue) => !venue.has_multiple_locations),
		...(placePin.value && !isMultiple.value ? [placePin.value] : []),
	])

	// One place, from the team's venues or from Google Maps, previewed before it is used.
	const preview = computed(() => {
		if (active.value)
			return {
				key: active.value.name,
				title: active.value.venue_name,
				address: active.value.address,
				source: "Saved venue",
			}
		if (activePlace.value)
			return {
				key: activePlace.value.place_id,
				title: activePlace.value.name,
				address: activePlace.value.address,
				source: "From Google Maps",
			}
		return null
	})

	function reset(locations: string[] = []) {
		isMultiple.value = locations.length > 0
		selected.value = locations
		active.value = null
		activePlace.value = null
		placePin.value = null
		hovered.value = null
	}

	// Switching keeps what was picked: the one place starts the list, the list's first is the one place.
	function setMultiple(value: boolean) {
		isMultiple.value = value
		if (value && active.value && !selected.value.length) selected.value = [active.value.name]
		if (!value && !active.value) active.value = chosen.value[0] ?? null
	}

	function pickVenue(venue: Venue) {
		if (!isMultiple.value) return choose(venue, null)
		const isPicked = selected.value.includes(venue.name)
		selected.value = isPicked
			? selected.value.filter((name) => name !== venue.name)
			: [...selected.value, venue.name]
	}

	// In a list, a Google Maps place is saved as a venue straight away, so it can be a location.
	async function pickPlace(place: PlacePrediction) {
		if (!isMultiple.value) return choose(null, place)
		isSaving.value = true
		const name = await picker.savePlace(place)
		isSaving.value = false
		if (name) add(name)
	}

	function add(name: string) {
		if (!selected.value.includes(name)) selected.value = [...selected.value, name]
	}

	function choose(venue: Venue | null, place: PlacePrediction | null) {
		active.value = venue
		activePlace.value = place
		placePin.value = null
		if (place) locate(place)
	}

	function locate(place: PlacePrediction) {
		addressLocation
			.submit({ address: place.address || place.name })
			.then((location) => {
				// A later pick may have replaced this one while it was being located.
				if (activePlace.value !== place || !location?.latitude || !location.longitude) return
				placePin.value = {
					name: place.place_id,
					venue_name: place.name,
					address: place.address,
					latitude: location.latitude,
					longitude: location.longitude,
				}
			})
			.catch(() => {})
	}

	/** Saves what is picked and answers with the venue to set on the event, or null on failure. */
	async function save() {
		isSaving.value = true
		const name = isMultiple.value
			? await picker.saveGroup(selected.value)
			: (active.value?.name ?? (activePlace.value && (await picker.savePlace(activePlace.value))))
		isSaving.value = false
		return name || null
	}

	return reactive({
		isMultiple,
		selected,
		hovered,
		isSaving,
		chosen,
		places,
		preview,
		activeName: computed(() => active.value?.name ?? activePlace.value?.place_id ?? null),
		reset,
		setMultiple,
		pickVenue,
		pickPlace,
		add,
		save,
	})
}
