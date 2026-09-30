<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed, ref, watch } from "vue"

import ZoomLogo from "@/components/common/ZoomLogo.vue"
import LocationDialog from "@/components/dashboard/events/location/LocationDialog.vue"
import { loadVenues, venues } from "@/data/venues"

const props = defineProps<{ team: string; disabled?: boolean; error?: string }>()
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
		<div
			v-if="chosenVenue || zoomMeeting"
			class="flex items-start gap-3 rounded-8 bg-surface-gray-2 p-3"
		>
			<ZoomLogo v-if="zoomMeeting" class="mt-0.5 size-5 shrink-0" />
			<span
				v-else
				class="lucide-map-pin mt-0.5 size-5 shrink-0 text-ink-gray-6"
				aria-hidden="true"
			/>
			<div class="min-w-0 flex-1">
				<p class="text-base font-medium text-ink-gray-9">
					{{ zoomMeeting ? "Zoom meeting" : chosenVenue?.venue_name }}
				</p>
				<p class="line-clamp-2 text-p-sm text-ink-gray-6">
					{{ zoomMeeting ? "Created when you save the event" : chosenVenue?.address }}
				</p>
			</div>
			<Button
				variant="ghost"
				icon="lucide-pencil"
				aria-label="Change location"
				:disabled="disabled"
				@click="isOpen = true"
			/>
			<Button
				variant="ghost"
				icon="lucide-x"
				aria-label="Remove location"
				:disabled="disabled"
				@click="clear"
			/>
		</div>
		<Button
			v-else
			class="!h-14 w-full"
			variant="subtle"
			icon-left="lucide-map-pin-plus"
			label="Add Location"
			:disabled="disabled"
			@click="isOpen = true"
		/>
		<ErrorMessage :message="error" />

		<LocationDialog v-model="isOpen" :team="team" @picked="pickVenue" @zoom="pickZoom" />
	</div>
</template>
