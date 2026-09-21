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

function cssValue(row: ThemeToken): string {
	if (row.type === "Font") return props.fonts[row.value] ?? ""
	return row.type === "Color" && row.dark_value
		? `light-dark(${row.value}, ${row.dark_value})`
		: row.value
}

// Unsaved values go straight onto the page's root as inline custom properties, which
// outrank the saved theme's :root block. The page is same-origin, so no messaging is needed.
function apply() {
	const root = frame.value?.contentDocument?.documentElement
	if (!root) return
	root.dataset.mode = props.colorScheme
	for (const row of props.tokens) {
		root.style.setProperty(`--${row.token}`, cssValue(row))
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
