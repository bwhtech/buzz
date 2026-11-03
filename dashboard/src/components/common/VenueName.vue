<script setup lang="ts">
// A venue with several locations opens them on the event page's map, so its whole name links there.
import { eventUrl } from "@/utils/eventUrl"

defineProps<{
	name: string
	eventRoute?: string | null
	hasMultipleLocations?: boolean
}>()
</script>

<template>
	<a
		v-if="hasMultipleLocations && eventRoute"
		:href="`${eventUrl(eventRoute)}#locations`"
		target="_blank"
		rel="noopener"
		class="underline underline-offset-2 transition-colors duration-150 hover:text-ink-gray-9"
		>{{ name }}</a
	>
	<span v-else>{{ name }}</span>
</template>
