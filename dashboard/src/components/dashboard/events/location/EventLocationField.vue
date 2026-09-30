<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed, ref, watch } from "vue"

import ChosenLocation from "@/components/dashboard/events/location/ChosenLocation.vue"
import LocationDialog from "@/components/dashboard/events/location/LocationDialog.vue"
import { loadVenues, venues } from "@/data/venues"

const props = withDefaults(
	defineProps<{ team: string; disabled?: boolean; error?: string; showZoom?: boolean }>(),
	{ error: "", showZoom: true },
)
const venue = defineModel<string>("venue", { default: "" })
const zoomMeeting = defineModel<boolean>("zoomMeeting", { default: false })

const isOpen = ref(false)

watch(
	() => props.team,
	(team) => team && loadVenues(team),
	{ immediate: true },
)

const chosenVenue = computed(() => (venues.data ?? []).find((row) => row.name === venue.value))

function pickVenue(name: string) {
	zoomMeeting.value = false
	venue.value = name
}

function pickZoom() {
	venue.value = ""
	zoomMeeting.value = true
}

function clear() {
	venue.value = ""
	zoomMeeting.value = false
}
</script>

<template>
	<div class="space-y-1.5">
		<ChosenLocation
			v-if="chosenVenue || zoomMeeting"
			:title="zoomMeeting ? 'Zoom meeting' : (chosenVenue?.venue_name ?? '')"
			:subtitle="zoomMeeting ? 'Created when you save the event' : chosenVenue?.address"
			:place-id="chosenVenue?.google_place_id"
			:latitude="chosenVenue?.latitude"
			:longitude="chosenVenue?.longitude"
			:is-zoom="zoomMeeting"
			:disabled="disabled"
			@change="isOpen = true"
			@remove="clear"
		/>
		<!-- An event opened with a venue waits for the list, rather than flashing Add Location. -->
		<Button
			v-else-if="!venue || !venues.loading"
			class="!h-14 w-full"
			variant="subtle"
			icon-left="lucide-map-pin-plus"
			label="Add Location"
			:disabled="disabled"
			@click="isOpen = true"
		/>
		<ErrorMessage :message="error" />

		<LocationDialog
			v-model="isOpen"
			:team="team"
			:show-zoom="showZoom"
			@picked="pickVenue"
			@zoom="pickZoom"
		/>
	</div>
</template>
