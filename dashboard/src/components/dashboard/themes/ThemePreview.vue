<script setup lang="ts">
import { ref, watch } from "vue"

import type { ThemeToken } from "@/types"
import { eventPath } from "@/utils/eventUrl"

const props = defineProps<{
	route: string
	tokens: ThemeToken[]
	colorScheme: string
	fonts: Record<string, string>
}>()

const frame = ref<HTMLIFrameElement>()

// Unsaved values go straight onto the page's root as inline custom properties, which
// outrank the saved theme's :root block. The page is same-origin, so no messaging is needed.
function apply() {
	const root = frame.value?.contentDocument?.documentElement
	if (!root) return
	root.style.colorScheme = props.colorScheme
	for (const row of props.tokens) {
		const value = row.type === "Font" ? (props.fonts[row.value] ?? "") : row.value
		root.style.setProperty(`--${row.token}`, value)
	}
}

watch(() => [props.tokens, props.colorScheme], apply, { deep: true })
</script>

<template>
	<iframe
		ref="frame"
		:src="eventPath(route)"
		:title="__('Theme preview')"
		class="size-full rounded-6 border border-outline-gray-2 bg-surface-white"
		@load="apply"
	/>
</template>
