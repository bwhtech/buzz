<script setup lang="ts">
import { Skeleton } from "frappe-ui"
import { computed, ref, watch } from "vue"

import LocationsMap from "@/components/dashboard/events/location/LocationsMap.vue"
import type { Venue } from "@/data/venues"

// The class lands on the map, not on whatever the fallback slot renders.
defineOptions({ inheritAttrs: false })

const props = defineProps<{
	title: string
	placeId?: string | null
	latitude?: number | null
	longitude?: number | null
	embedUrl?: string | null
}>()

const PREVIEW_PADDING = { top: 24, right: 24, bottom: 24, left: 24 }

const isLoaded = ref(false)
// The skeleton stays until the map has finished fading in over it.
const isRevealed = ref(false)

// A place with coordinates is drawn on the location picker's map, in the same theme.
const place = computed<Venue | null>(() => {
	const { latitude, longitude, title } = props
	if (!latitude || !longitude) return null
	return { name: title, venue_name: title, address: null, latitude, longitude }
})
const places = computed(() => (place.value ? [place.value] : []))

const googleUrl = computed(() => {
	const key = window.google_maps_embed_api_key
	if (!key || !props.placeId) return ""
	const search = new URLSearchParams({ key, q: `place_id:${props.placeId}` })
	return `https://www.google.com/maps/embed/v1/place?${search}`
})

const url = computed(() => googleUrl.value || props.embedUrl)

watch(url, () => {
	isLoaded.value = false
	isRevealed.value = false
})
</script>

<template>
	<div v-if="place" v-bind="$attrs" class="relative overflow-hidden">
		<!-- Keyed by coordinates: a new place mounts a new map framed on it. -->
		<LocationsMap
			:key="`${place.latitude},${place.longitude}`"
			class="absolute inset-0"
			:places="places"
			:selected="[]"
			:active="place.name"
			:hovered="null"
			:padding="PREVIEW_PADDING"
			readonly
		/>
	</div>
	<div v-else-if="url" v-bind="$attrs" class="relative overflow-hidden">
		<Skeleton v-if="!isRevealed" class="absolute inset-0 rounded-none" />
		<!-- Keyed by place: a new place mounts a new iframe, because changing `src` on a live
		 one adds a browser history entry. -->
		<iframe
			:key="url"
			class="relative size-full border-0 transition-opacity duration-200 ease-out"
			:class="isLoaded ? 'opacity-100' : 'opacity-0'"
			:src="url"
			:title="`Map of ${title}`"
			referrerpolicy="no-referrer-when-downgrade"
			@load="isLoaded = true"
			@transitionend="isRevealed = true"
		/>
	</div>
	<slot v-else />
</template>
