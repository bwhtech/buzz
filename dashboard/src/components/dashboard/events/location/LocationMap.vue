<script setup lang="ts">
import { computed, ref } from "vue"

// The class lands on the map, not on whatever the fallback slot renders.
defineOptions({ inheritAttrs: false })

const props = defineProps<{ placeId?: string | null; title: string }>()

const isLoaded = ref(false)

const url = computed(() => {
	const key = window.google_maps_embed_api_key
	if (!key || !props.placeId) return ""
	const search = new URLSearchParams({ key, q: `place_id:${props.placeId}` })
	return `https://www.google.com/maps/embed/v1/place?${search}`
})
</script>

<template>
	<!-- Keyed by place: a new place mounts a new iframe, because changing `src` on a live
	 one adds a browser history entry. -->
	<iframe
		v-if="url"
		:key="url"
		v-bind="$attrs"
		class="w-full border-0 transition-opacity duration-200 ease-out"
		:class="isLoaded ? 'opacity-100' : 'opacity-0'"
		:src="url"
		:title="`Map of ${title}`"
		referrerpolicy="no-referrer-when-downgrade"
		@vue:before-mount="isLoaded = false"
		@load="isLoaded = true"
	/>
	<slot v-else />
</template>
