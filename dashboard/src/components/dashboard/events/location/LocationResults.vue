<script setup lang="ts">
import LocationRow from "@/components/dashboard/events/location/LocationRow.vue"
import type { LocationPicker } from "@/components/dashboard/events/location/useLocationPicker"
import type { PlacePrediction, Venue } from "@/data/venues"

defineProps<{ picker: LocationPicker; activeKey?: string }>()
defineEmits<{ venue: [venue: Venue]; place: [place: PlacePrediction] }>()
</script>

<template>
	<div class="space-y-3">
		<section v-if="picker.savedVenues.length">
			<h3 class="px-2 pb-1 text-sm text-ink-gray-5">Your venues</h3>
			<LocationRow
				v-for="venue in picker.savedVenues"
				:key="venue.name"
				icon="lucide-map-pin"
				:title="venue.venue_name"
				:subtitle="venue.address"
				:active="activeKey === venue.name"
				@click="$emit('venue', venue)"
			/>
		</section>
		<section v-if="picker.places.length">
			<h3 class="px-2 pb-1 text-sm text-ink-gray-5">Google Maps</h3>
			<LocationRow
				v-for="place in picker.places"
				:key="place.place_id"
				icon="lucide-search"
				:title="place.name"
				:subtitle="place.address"
				:active="activeKey === place.place_id"
				@click="$emit('place', place)"
			/>
		</section>
		<p
			v-if="!picker.savedVenues.length && !picker.places.length"
			class="px-2 py-6 text-center text-p-sm text-ink-gray-5"
		>
			{{
				picker.query
					? "No venue matches. Add it manually instead."
					: "No venues yet. Search for a place."
			}}
		</p>
	</div>
</template>
