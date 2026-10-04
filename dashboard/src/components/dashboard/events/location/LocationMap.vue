<script setup lang="ts">
import { Skeleton } from "frappe-ui"
import { computed, ref, watch } from "vue"

// The class lands on the map, not on whatever the fallback slot renders.
defineOptions({ inheritAttrs: false })

const props = defineProps<{
	title: string
	placeId?: string | null
	latitude?: number | null
	longitude?: number | null
	embedUrl?: string | null
}>()

const OPEN_STREET_MAP_SPAN_DEGREES = 0.01

const isLoaded = ref(false)
// The skeleton stays until the map has finished fading in over it.
const isRevealed = ref(false)

const googleUrl = computed(() => {
	const key = window.google_maps_embed_api_key
	if (!key || !props.placeId) return ""
	const search = new URLSearchParams({ key, q: `place_id:${props.placeId}` })
	return `https://www.google.com/maps/embed/v1/place?${search}`
})

// Same box and marker as the event page draws for a venue with coordinates.
const openStreetMapUrl = computed(() => {
	const { latitude, longitude } = props
	if (!latitude || !longitude) return ""
	const span = OPEN_STREET_MAP_SPAN_DEGREES
	const search = new URLSearchParams({
		bbox: [longitude - span, latitude - span, longitude + span, latitude + span].join(","),
		layer: "mapnik",
		marker: `${latitude},${longitude}`,
	})
	return `https://www.openstreetmap.org/export/embed.html?${search}`
})

const url = computed(() => googleUrl.value || props.embedUrl || openStreetMapUrl.value)

watch(url, () => {
	isLoaded.value = false
	isRevealed.value = false
})
</script>

<template>
	<div v-if="url" v-bind="$attrs" class="relative overflow-hidden">
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
