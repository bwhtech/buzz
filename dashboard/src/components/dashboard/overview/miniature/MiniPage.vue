<script setup lang="ts">
import type { StepEvent } from "../setupSteps"

// The event page as guests see it: cover, title, the opening lines.
// Empty: the drop area for a cover over a blank page.
defineProps<{ done: boolean; event: StepEvent }>()

const LINES = ["100%", "92%", "100%", "64%"]
</script>

<template>
	<div class="mini-panel overflow-hidden p-1.5">
		<div v-if="done" class="mini-banner aspect-[2/1] rounded-[6px]" />
		<div
			v-else
			class="flex aspect-[2/1] flex-col items-center justify-center gap-1 rounded-[6px] border border-dashed border-outline-gray-3 text-ink-gray-5"
		>
			<span class="lucide-image-plus size-3.5" />
			<span class="mini-value">1600 × 800</span>
		</div>
		<div class="space-y-2 px-1.5 pb-6 pt-2.5">
			<p class="truncate text-[13px] font-semibold leading-[18px] text-ink-gray-9">
				{{ event.title }}
			</p>
			<p v-if="done" class="text-ink-gray-6">
				An evening of talks and demos from the community. Bring a laptop and stay for dinner.
			</p>
			<p v-else class="mini-empty">Tell guests what to expect</p>
			<div class="space-y-1.5 pt-1" :class="!done && 'opacity-60'">
				<span v-for="width in LINES" :key="width" class="mini-bar" :style="{ width }" />
			</div>
		</div>
	</div>
</template>

<style scoped>
/* A cover in greys only: fine diagonal rules over a soft ramp. */
.mini-banner {
	background:
		repeating-linear-gradient(135deg, transparent 0 7px, var(--outline-gray-2) 7px 8px),
		linear-gradient(160deg, var(--surface-gray-2), var(--surface-gray-4));
	transition: background-position 600ms cubic-bezier(0.23, 1, 0.32, 1);
}
:global(.setup-card:is(:hover, :focus-within)) .mini-banner {
	background-position:
		12px 0,
		0 0;
}
</style>
