<script setup lang="ts">
// Picks an event's location over a map of the team's places: one place, or several for a
// venue with multiple locations. A dialog on desktop; a full-screen map with a sheet on phones.
import { Button, Dialog } from "frappe-ui"
import { DialogClose, DialogContent, DialogPortal, DialogRoot, DialogTitle } from "reka-ui"
import { computed, watch } from "vue"

import ChosenPlaces from "@/components/dashboard/events/location/ChosenPlaces.vue"
import LocationNumber from "@/components/dashboard/events/location/LocationNumber.vue"
import LocationPanel from "@/components/dashboard/events/location/LocationPanel.vue"
import LocationsMap from "@/components/dashboard/events/location/LocationsMap.vue"
import { useLocationPicker } from "@/components/dashboard/events/location/useLocationPicker"
import { useLocationSelection } from "@/components/dashboard/events/location/useLocationSelection"
import { useIsMobile } from "@/composables/useIsMobile"
import { isFeatureEnabled } from "@/data/teams"
import { useVenueLocations, venues } from "@/data/venues"

// Pages that book Zoom another way leave the Zoom option out; a site without Zoom never shows it.
const props = withDefaults(
	defineProps<{ team: string; showZoom?: boolean; title?: string; venue?: string }>(),
	{ showZoom: true, title: "Add location", venue: "" },
)
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ picked: [venue: string]; zoom: [] }>()

const isMobile = useIsMobile()
const picker = useLocationPicker(() => props.team, isOpen)
const selection = useLocationSelection(picker)
const groupLocations = useVenueLocations(() => props.venue)
const canPickZoom = computed(() => props.showZoom && Boolean(window.zoom_available))
// An event page does not switch the current team, so the flag is read for the event's team.
const canPickMultiple = computed(() => isFeatureEnabled("feature_multiple_locations", props.team))
const hasChosen = computed(() => selection.isMultiple && selection.chosen.length > 0)
const useLabel = computed(() => {
	if (!selection.isMultiple) return "Use this location"
	const count = selection.chosen.length
	return count < 2 ? "Pick at least 2 locations" : `Use ${count} locations`
})
const canUse = computed(() =>
	selection.isMultiple ? selection.chosen.length > 1 : Boolean(selection.preview),
)
const hint = computed(() => {
	if (selection.isMultiple)
		return selection.chosen.length ? "" : "Click dots on the map or venues in the list"
	return selection.preview ? "" : "Pick a venue to see it on the map"
})

// Changing a venue with several locations starts from its places.
watch(isOpen, (open) => {
	if (!open) return
	selection.reset()
	const current = venues.data?.find((venue) => venue.name === props.venue)
	if (!current?.has_multiple_locations) return
	groupLocations
		.submit()
		.then((group) => group && selection.reset(group.locations.map((row) => row.venue)))
		.catch(() => {})
})

function pick(venue: string | null) {
	if (!venue) return
	emit("picked", venue)
	isOpen.value = false
}

function use() {
	selection.save().then(pick)
}

function pickZoom() {
	emit("zoom")
	isOpen.value = false
}

const mapProps = computed(() => ({
	places: selection.places,
	selected: selection.isMultiple ? selection.selected : [],
	active: selection.isMultiple ? null : selection.activeName,
	hovered: selection.hovered,
}))
</script>

<template>
	<Dialog v-if="!isMobile" v-model="isOpen" bare size="5xl">
		<div class="relative h-[min(600px,calc(100dvh-6rem))] bg-surface-gray-2">
			<LocationsMap
				class="absolute inset-0"
				v-bind="mapProps"
				:padding="{ top: 48, right: hasChosen ? 300 : 48, bottom: 48, left: 372 }"
				@pick="selection.pickVenue"
			/>
			<LocationPanel
				class="absolute bottom-3 left-3 top-3 z-10 w-[340px] overflow-hidden rounded-6 border border-outline-gray-1 bg-surface-elevation-1 shadow-lg"
				:picker="picker"
				:selection="selection"
				:title="title"
				:can-pick-zoom="canPickZoom"
				:can-pick-multiple="canPickMultiple"
				show-header
				@picked="pick"
				@zoom="pickZoom"
			/>
			<Transition
				enter-active-class="transition duration-200 ease-out"
				enter-from-class="opacity-0 scale-[0.97]"
				leave-active-class="transition duration-150 ease-out"
				leave-to-class="opacity-0 scale-[0.97]"
			>
				<ChosenPlaces
					v-if="hasChosen"
					v-model="selection.selected"
					class="absolute right-3 top-3 z-10 max-h-[calc(100%-1.5rem)] w-[272px] origin-top-right rounded-6 border border-outline-gray-1 bg-surface-elevation-1 shadow-lg"
					:places="selection.chosen"
					:hovered="selection.hovered"
					:is-saving="selection.isSaving"
					@hover="selection.hovered = $event"
					@use="use"
				/>
				<div
					v-else-if="!selection.isMultiple && selection.preview"
					class="absolute bottom-3 right-3 z-10 flex w-[300px] origin-bottom-right flex-col gap-1.5 rounded-6 border border-outline-gray-1 bg-surface-elevation-1 p-3.5 shadow-lg"
				>
					<p class="flex items-center gap-1.5 text-sm text-ink-gray-5">
						{{ selection.preview.source }}
						<template v-if="selection.isLocating">
							<span aria-hidden="true">·</span>
							<span class="lucide-loader-circle size-3 animate-spin" aria-hidden="true" />
							<span role="status">Finding on map</span>
						</template>
					</p>
					<p class="text-lg font-semibold text-ink-gray-9">{{ selection.preview.title }}</p>
					<p v-if="selection.preview.address" class="mb-1.5 text-p-sm text-ink-gray-6">
						{{ selection.preview.address }}
					</p>
					<Button variant="solid" :label="useLabel" :loading="selection.isSaving" @click="use" />
				</div>
			</Transition>
			<p
				v-if="hint"
				class="pointer-events-none absolute bottom-5 left-[364px] right-3 z-10 flex justify-center"
			>
				<span
					class="rounded-full border border-outline-gray-1 bg-surface-elevation-1 px-3 py-1.5 text-p-sm text-ink-gray-7 shadow-md"
				>
					{{ hint }}
				</span>
			</p>
		</div>
	</Dialog>

	<DialogRoot v-else v-model:open="isOpen">
		<DialogPortal>
			<DialogContent class="fixed inset-0 z-50 bg-surface-gray-2" :aria-describedby="undefined">
				<LocationsMap
					class="absolute inset-0"
					v-bind="mapProps"
					:padding="{ top: hasChosen ? 150 : 90, right: 28, bottom: 420, left: 28 }"
					@pick="selection.pickVenue"
				/>
				<div
					class="absolute inset-x-3 top-[max(0.75rem,env(safe-area-inset-top))] z-10 flex flex-col gap-2"
				>
					<div class="flex items-center gap-2">
						<DialogClose as-child>
							<Button
								class="!size-11 shrink-0 !rounded-full shadow-md"
								variant="outline"
								icon="lucide-x"
								aria-label="Close"
							/>
						</DialogClose>
						<DialogTitle
							class="flex h-11 flex-1 items-center rounded-full border border-outline-gray-1 bg-surface-elevation-1 px-4 text-lg font-semibold text-ink-gray-9 shadow-md"
						>
							{{ title }}
						</DialogTitle>
					</div>
					<TransitionGroup
						v-if="hasChosen"
						tag="ol"
						class="flex gap-1.5 overflow-x-auto pb-1 [scrollbar-width:none]"
						enter-active-class="transition duration-200 ease-out"
						enter-from-class="opacity-0 scale-95"
					>
						<li
							v-for="(place, index) in selection.chosen"
							:key="place.name"
							class="flex h-9 max-w-[180px] shrink-0 items-center gap-1.5 rounded-full border border-outline-gray-1 bg-surface-elevation-1 px-1 shadow-sm"
						>
							<LocationNumber :number="index + 1" class="!size-6" />
							<span class="truncate text-sm text-ink-gray-8">{{ place.venue_name }}</span>
							<Button
								size="sm"
								variant="ghost"
								icon="lucide-x"
								class="!rounded-full"
								:aria-label="`Remove ${place.venue_name}`"
								@click="selection.pickVenue(place)"
							/>
						</li>
					</TransitionGroup>
				</div>
				<div
					class="absolute inset-x-0 bottom-0 z-10 flex h-[min(390px,60dvh)] flex-col rounded-t-[20px] border-t border-outline-gray-1 bg-surface-elevation-1 shadow-2xl"
				>
					<div class="flex justify-center pb-2.5 pt-2" aria-hidden="true">
						<span class="h-1 w-9 rounded-full bg-surface-gray-4" />
					</div>
					<LocationPanel
						class="min-h-0 flex-1"
						:picker="picker"
						:selection="selection"
						:title="title"
						:can-pick-zoom="canPickZoom"
						:can-pick-multiple="canPickMultiple"
						@picked="pick"
						@zoom="pickZoom"
					/>
					<div
						v-if="selection.isMultiple ? hasChosen : selection.preview"
						class="border-t border-outline-gray-1 px-4 pb-[max(1.75rem,env(safe-area-inset-bottom))] pt-3"
					>
						<Button
							class="w-full"
							size="lg"
							variant="solid"
							:label="useLabel"
							:disabled="!canUse"
							:loading="selection.isSaving"
							@click="use"
						/>
					</div>
				</div>
			</DialogContent>
		</DialogPortal>
	</DialogRoot>
</template>
