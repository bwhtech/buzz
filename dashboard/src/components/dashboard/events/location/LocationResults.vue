<script setup lang="ts">
import LocationRow from "@/components/dashboard/events/location/LocationRow.vue"
import LocationRowSkeleton from "@/components/dashboard/events/location/LocationRowSkeleton.vue"
import type { LocationPicker } from "@/components/dashboard/events/location/useLocationPicker"
import type { PlacePrediction, Venue } from "@/data/venues"

// `selected` is set when several places are being picked: rows then check on and off.
const props = defineProps<{ picker: LocationPicker; activeKey?: string; selected?: string[] }>()
defineEmits<{
	venue: [venue: Venue]
	place: [place: PlacePrediction]
	manual: []
	hover: [venue: string | null]
}>()

function numberOf(venue: string) {
	return (props.selected?.indexOf(venue) ?? -1) + 1 || undefined
}
</script>

<template>
	<div class="space-y-3">
		<section v-if="picker.savedVenues.length || picker.isLoadingVenues">
			<h3 class="px-2 pb-1 text-sm text-ink-gray-5">Your venues</h3>
			<LocationRowSkeleton v-if="picker.isLoadingVenues" label="Loading your venues…" />
			<LocationRow
				v-for="venue in picker.savedVenues"
				:key="venue.name"
				icon="lucide-map-pin"
				:title="venue.venue_name"
				:subtitle="venue.address"
				:active="activeKey === venue.name"
				:checked="selected ? selected.includes(venue.name) : undefined"
				:number="numberOf(venue.name)"
				@click="$emit('venue', venue)"
				@pointerenter="$emit('hover', venue.name)"
				@pointerleave="$emit('hover', null)"
			/>
		</section>
		<!-- Earlier results stay up while the next search runs; the skeleton is only for a first one. -->
		<section v-if="picker.places.length || picker.isSearching">
			<h3 class="px-2 pb-1 text-sm text-ink-gray-5">Google Maps</h3>
			<LocationRowSkeleton v-if="!picker.places.length" label="Searching Google Maps…" />
			<LocationRow
				v-for="place in picker.places"
				:key="place.place_id"
				icon="lucide-search"
				:title="place.name"
				:subtitle="place.address"
				:active="activeKey === place.place_id"
				:checked="selected ? false : undefined"
				@click="$emit('place', place)"
			/>
		</section>
		<!-- Shown as the active row because Enter in the search box takes it. -->
		<LocationRow
			v-if="picker.isUnmatched"
			icon="lucide-map-pin-plus"
			:title="`Add “${picker.query.trim()}” manually`"
			subtitle="No venue matches. Press Enter to add it."
			active
			@click="$emit('manual')"
		/>
		<p
			v-else-if="!picker.savedVenues.length && !picker.isSearching && !picker.isLoadingVenues"
			class="px-2 py-6 text-center text-p-sm text-ink-gray-5"
		>
			No venues yet. Search for a place, or type a name to add one.
		</p>
	</div>
</template>
