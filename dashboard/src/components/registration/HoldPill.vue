<template>
	<div
		class="flex flex-none items-center gap-1.5 rounded-full border border-outline-gray-2 bg-surface-base px-2.5 py-1 text-p-sm tabular-nums text-ink-gray-7"
	>
		<LucideTimer class="size-3.5" />
		<span>{{ compact ? clock : __("Held for {0}", [clock]) }}</span>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import LucideTimer from "~icons/lucide/timer"

const props = defineProps<{ secondsLeft: number; compact?: boolean }>()

const clock = computed(
	() => `${Math.floor(props.secondsLeft / 60)}:${String(props.secondsLeft % 60).padStart(2, "0")}`,
)
</script>
