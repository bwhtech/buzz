<script setup lang="ts">
import { bannerPattern } from "@public/js/event_banner"
import { computed } from "vue"

import type { CommunityRequest } from "@/types"

// A Buzz event shows its banner; an external one, a link tile.
const props = defineProps<{ request: CommunityRequest }>()

const banner = computed(() => ({ backgroundImage: bannerPattern(props.request.event_title) }))
</script>

<template>
	<span
		v-if="request.is_external_event"
		class="flex size-10 shrink-0 items-center justify-center rounded-4 border border-dashed border-outline-gray-3 bg-surface-gray-1 text-ink-gray-5"
		aria-hidden="true"
	>
		<span class="lucide-link size-5" />
	</span>
	<img
		v-else-if="request.banner_image"
		class="size-10 shrink-0 rounded-4 object-cover object-top"
		:src="request.banner_image"
		:style="banner"
		alt=""
	/>
	<span v-else class="size-10 shrink-0 rounded-4" :style="banner" aria-hidden="true" />
</template>
