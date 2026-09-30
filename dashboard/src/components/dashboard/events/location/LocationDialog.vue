<script setup lang="ts">
import { Button, Dialog, Divider, ScrollArea, Skeleton, TextInput } from "frappe-ui"
import { ref, watch } from "vue"

import ZoomLogo from "@/components/common/ZoomLogo.vue"
import LocationMap from "@/components/dashboard/events/location/LocationMap.vue"
import LocationResults from "@/components/dashboard/events/location/LocationResults.vue"
import ManualVenueForm from "@/components/dashboard/events/location/ManualVenueForm.vue"
import { useLocationPicker } from "@/components/dashboard/events/location/useLocationPicker"
import type { MapLinkLocation, PlacePrediction, Venue } from "@/data/venues"

interface Preview {
	key: string
	title: string
	address: string | null
	source: string
	placeId?: string | null
	latitude?: number
	longitude?: number
	use: () => Promise<string | null> | string
}

// Zoom is booked only when the event is created, so a page editing one leaves it out.
const props = withDefaults(defineProps<{ team: string; showZoom?: boolean }>(), { showZoom: true })
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ picked: [venue: string]; zoom: [] }>()

const picker = useLocationPicker(() => props.team, isOpen)
const preview = ref<Preview | null>(null)
const isAddingManually = ref(false)
const isSaving = ref(false)
// What the manual form's map link turned out to point at, with the name typed so far.
const manualLocation = ref<(MapLinkLocation & { title: string }) | null>(null)

watch(isOpen, (open) => {
	if (!open) return
	preview.value = null
	isAddingManually.value = false
})

function previewVenue(venue: Venue) {
	preview.value = {
		key: venue.name,
		title: venue.venue_name,
		address: venue.address,
		source: "Saved venue",
		placeId: venue.google_place_id,
		latitude: venue.latitude,
		longitude: venue.longitude,
		use: () => venue.name,
	}
}

function previewPlace(place: PlacePrediction) {
	preview.value = {
		key: place.place_id,
		title: place.name,
		address: place.address,
		source: "From Google Maps",
		placeId: place.place_id,
		use: () => picker.savePlace(place),
	}
}

const isLocating = ref(false)

function showManualLocation(location: MapLinkLocation | null, title: string) {
	isLocating.value = false
	manualLocation.value = location && { ...location, title }
}

function addManually() {
	preview.value = null
	manualLocation.value = null
	isLocating.value = false
	isAddingManually.value = true
}

function pick(venue: string | null) {
	if (!venue) return
	emit("picked", venue)
	isOpen.value = false
}

async function usePreview() {
	if (!preview.value) return
	isSaving.value = true
	pick(await preview.value.use())
	isSaving.value = false
}

function pickZoom() {
	emit("zoom")
	isOpen.value = false
}
</script>

<template>
	<Dialog
		v-model="isOpen"
		size="3xl"
		:title="isAddingManually ? 'Add venue manually' : 'Add location'"
	>
		<!-- Dialog's `size` only caps the width. This height is the one the results scroll
		 inside, and the manual form shares it, so switching does not resize the dialog. -->
		<div class="grid gap-4 md:h-96 md:grid-cols-2">
			<Transition
				mode="out-in"
				enter-active-class="transition-opacity duration-150 ease-out"
				enter-from-class="opacity-0"
				leave-active-class="transition-opacity duration-100 ease-out"
				leave-to-class="opacity-0"
			>
				<ManualVenueForm
					v-if="isAddingManually"
					:picker="picker"
					:suggested-name="picker.query.trim()"
					@saved="pick"
					@cancel="isAddingManually = false"
					@locating="isLocating = true"
					@located="showManualLocation"
				/>
				<div v-else class="flex min-h-0 flex-col gap-3">
					<TextInput
						v-model="picker.query"
						placeholder="Search a venue or a place"
						autofocus
						@keydown.enter.prevent="picker.isUnmatched && addManually()"
					>
						<template #prefix>
							<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
						</template>
					</TextInput>
					<ScrollArea class="h-72 shrink-0">
						<LocationResults
							:picker="picker"
							:active-key="preview?.key"
							:inert="isSaving"
							class="transition-opacity duration-150 ease-out"
							:class="isSaving && 'opacity-60'"
							@venue="previewVenue"
							@place="previewPlace"
							@manual="addManually"
						/>
					</ScrollArea>
					<ErrorMessage :message="picker.error" />
					<Divider />
					<div class="flex gap-2">
						<Button
							variant="ghost"
							icon-left="lucide-map-pin-plus"
							label="Add manually"
							@click="addManually"
						/>
						<Button v-if="showZoom" variant="ghost" label="Zoom meeting" @click="pickZoom">
							<template #prefix>
								<ZoomLogo class="size-4" color="var(--ink-gray-5)" />
							</template>
						</Button>
					</div>
				</div>
			</Transition>

			<div class="flex min-h-72 flex-col overflow-hidden rounded-5 bg-surface-gray-1 md:min-h-0">
				<template v-if="preview">
					<LocationMap
						class="h-48"
						:place-id="preview.placeId"
						:latitude="preview.latitude"
						:longitude="preview.longitude"
						:title="preview.title"
					>
						<div class="flex h-48 items-center justify-center text-ink-gray-4">
							<span class="lucide-map size-8" aria-hidden="true" />
						</div>
					</LocationMap>
					<div class="flex flex-1 flex-col gap-1 p-4">
						<p class="text-sm text-ink-gray-5">{{ preview.source }}</p>
						<p class="text-lg font-medium text-ink-gray-9">{{ preview.title }}</p>
						<p v-if="preview.address" class="text-p-sm text-ink-gray-6">
							{{ preview.address }}
						</p>
						<Button
							class="mt-auto w-full"
							variant="solid"
							label="Use this location"
							:loading="isSaving"
							@click="usePreview"
						/>
					</div>
				</template>
				<div v-else-if="isAddingManually && isLocating" class="flex-1" aria-busy="true">
					<span class="sr-only">Reading the map link…</span>
					<Skeleton class="size-full min-h-48 rounded-none" />
				</div>
				<LocationMap
					v-else-if="isAddingManually && manualLocation"
					class="h-full min-h-48"
					:latitude="manualLocation.latitude"
					:longitude="manualLocation.longitude"
					:embed-url="manualLocation.embed_url"
					:title="manualLocation.title"
				>
					<div class="flex flex-1 items-center justify-center p-6 text-center text-ink-gray-5">
						<p class="text-p-sm">This link does not show a location. Add the address instead.</p>
					</div>
				</LocationMap>
				<div
					v-else
					class="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-ink-gray-5"
				>
					<span class="lucide-map-pin size-6" aria-hidden="true" />
					<p class="text-p-sm">
						{{
							isAddingManually
								? "Paste a map link to see the place here."
								: "Pick a venue or a place to see it here before you add it."
						}}
					</p>
				</div>
			</div>
		</div>
	</Dialog>
</template>
