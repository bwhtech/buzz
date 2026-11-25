<script setup lang="ts">
import { computed, ref } from "vue"

import type { EventSummary } from "./overviewData"
import SetupCard from "./SetupCard.vue"
import type { SetupCardStep } from "./setupSteps"

const props = defineProps<{ steps: SetupCardStep[]; summary: EventSummary }>()

const doneCount = computed(() => props.steps.filter((step) => step.done).length)
const allDone = computed(() => doneCount.value === props.steps.length)

// Hosts who don't want the cards can fold them away; the header stays as one line.
const open = ref(true)
</script>

<template>
	<section class="space-y-3">
		<header class="flex h-7 items-center gap-3">
			<button
				type="button"
				class="setup-toggle -ml-1.5 flex min-w-0 items-center gap-1.5 rounded-4 py-0.5 pl-1.5 pr-2"
				:aria-expanded="open"
				@click="open = !open"
			>
				<h2 class="text-lg font-semibold text-ink-gray-9">
					{{ allDone ? "You're all set" : "Finish setting up" }}
				</h2>
				<span
					class="setup-chevron lucide-chevron-down size-4 text-ink-gray-5"
					:data-open="open || undefined"
				/>
			</button>
			<div class="ml-auto flex w-40 shrink-0 flex-col items-end gap-1.5">
				<span class="text-sm tabular-nums text-ink-gray-6">
					{{ doneCount }} of {{ steps.length }} done
				</span>
				<span class="h-1 w-full overflow-hidden rounded-full bg-surface-gray-2">
					<span
						class="setup-progress block h-full origin-left rounded-full bg-[var(--ink-gray-9)]"
						:style="{ transform: `scaleX(${doneCount / steps.length})` }"
					/>
				</span>
			</div>
		</header>

		<div class="setup-body grid" :data-open="open || undefined">
			<div class="setup-body-inner min-h-0">
				<div class="grid gap-4 pt-1 sm:grid-cols-2 lg:grid-cols-3">
					<SetupCard v-for="step in steps" :key="step.key" :step="step" :event="summary" />
				</div>
			</div>
		</div>
	</section>
</template>

<style scoped>
.setup-toggle {
	transition:
		background-color 150ms ease,
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.setup-toggle:active {
	transform: scale(0.98);
}
@media (hover: hover) and (pointer: fine) {
	.setup-toggle:hover {
		background: var(--surface-gray-2);
	}
}
.setup-chevron {
	transform: rotate(-90deg);
	transition: transform 220ms cubic-bezier(0.23, 1, 0.32, 1);
}
.setup-chevron[data-open] {
	transform: none;
}
.setup-progress {
	transition: transform 300ms cubic-bezier(0.23, 1, 0.32, 1);
}
/* Rows 0fr to 1fr: the body folds to its own height without measuring it. */
.setup-body {
	grid-template-rows: 0fr;
	opacity: 0;
	transition:
		grid-template-rows 260ms cubic-bezier(0.23, 1, 0.32, 1),
		opacity 180ms ease;
}
.setup-body[data-open] {
	grid-template-rows: 1fr;
	opacity: 1;
}
.setup-body:not([data-open]) > .setup-body-inner {
	overflow: hidden;
}
@media (prefers-reduced-motion: reduce) {
	.setup-body {
		transition: opacity 180ms ease;
	}
}
</style>
