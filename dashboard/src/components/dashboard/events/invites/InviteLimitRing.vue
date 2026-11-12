<script setup lang="ts">
import { computed } from "vue"

const props = defineProps<{ used: number; limit: number }>()

const RADIUS = 6
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

const left = computed(() => Math.max(props.limit - props.used, 0))
const offset = computed(() => CIRCUMFERENCE * (1 - Math.min(props.used / props.limit, 1)))
const tone = computed(() =>
	left.value === 0 ? "text-ink-red-6" : left.value <= 5 ? "text-ink-amber-6" : "text-ink-gray-7",
)
</script>

<template>
	<span
		class="flex items-center gap-1.5 rounded-full border border-outline-gray-2 py-1 pl-1.5 pr-2.5 text-p-xs font-medium uppercase tabular-nums tracking-wide"
		:class="tone"
		role="status"
		:aria-label="`${left} of ${limit} invites left in this batch`"
	>
		<svg class="size-4 -rotate-90" viewBox="0 0 16 16" aria-hidden="true">
			<circle
				cx="8"
				cy="8"
				:r="RADIUS"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				class="opacity-20"
			/>
			<circle
				cx="8"
				cy="8"
				:r="RADIUS"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				:stroke-dasharray="CIRCUMFERENCE"
				:stroke-dashoffset="offset"
				class="ring-progress"
			/>
		</svg>
		{{ left }} left
	</span>
</template>

<style scoped>
.ring-progress {
	transition: stroke-dashoffset 250ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.ring-progress {
		transition: none;
	}
}
</style>
