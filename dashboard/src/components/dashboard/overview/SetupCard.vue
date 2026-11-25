<script setup lang="ts">
import MiniatureArt from "./miniature/MiniatureArt.vue"
import type { SetupCardStep, StepEvent } from "./setupSteps"

// One setup step: the screen it opens, drawn small. The whole card links to that page.
defineProps<{ step: SetupCardStep; event: StepEvent }>()
</script>

<template>
	<article
		class="setup-card relative flex flex-col overflow-hidden rounded-5 bg-surface-gray-1"
		:data-done="step.done || undefined"
	>
		<div class="setup-text space-y-1 pr-6">
			<h3 class="text-lg font-semibold tracking-[-0.01em] text-ink-gray-9">
				<router-link
					:to="step.to"
					class="after:absolute after:inset-0 focus-visible:outline-none"
					:aria-label="step.done ? `${step.title} (done)` : step.title"
				>
					{{ step.title }}
				</router-link>
			</h3>
			<p class="text-p-sm text-ink-gray-5">{{ step.hint }}</p>
		</div>

		<!-- The art lets clicks through to the card's link underneath. -->
		<div
			class="setup-stage pointer-events-none relative z-10 mt-auto h-32 shrink-0 overflow-hidden"
		>
			<MiniatureArt :step="step.key" :done="step.done" :event="event" />
		</div>

		<div
			class="setup-overlay pointer-events-none absolute inset-0 z-20 grid place-items-center"
			aria-hidden="true"
		>
			<span class="flex items-center gap-2 text-base font-medium text-ink-gray-9">
				<span class="setup-tick"><span class="lucide-check size-3" /></span>
				Done
			</span>
		</div>
	</article>
</template>

<style scoped>
.setup-card {
	transition: transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.setup-card:active {
	transform: scale(0.99);
}
.setup-card:has(:focus-visible) {
	outline: 2px solid var(--outline-gray-4);
	outline-offset: 2px;
}
.setup-text {
	padding: 20px 20px 0;
}

/* The art hangs from the top of its slot and fades out before the card's bottom
   edge, so it reads as a window into the screen. */
.setup-stage {
	margin-top: 16px;
	-webkit-mask-image: linear-gradient(#000 50%, transparent 100%);
	mask-image: linear-gradient(#000 50%, transparent 100%);
}

/* Done: the darkest ink, the card's own surface for the tick, so it inverts in dark mode. */
.setup-tick {
	display: grid;
	place-items: center;
	width: 20px;
	height: 20px;
	border-radius: 999px;
	background: var(--ink-gray-9);
	color: var(--surface-elevation-1);
}

/* A finished card steps back behind a centred "Done"; looking at it (hover or focus)
   lifts the label away and brings the card back. */
.setup-text,
.setup-stage,
.setup-overlay {
	transition:
		opacity 200ms ease,
		filter 200ms ease,
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.setup-overlay {
	opacity: 0;
	transform: scale(0.96);
	filter: blur(2px);
}
.setup-card[data-done] .setup-overlay {
	opacity: 1;
	transform: none;
	filter: none;
}
.setup-card[data-done] :is(.setup-text, .setup-stage) {
	opacity: 0.18;
	filter: grayscale(1);
}
.setup-card[data-done]:focus-within .setup-overlay {
	opacity: 0;
	transform: scale(0.96);
	filter: blur(2px);
}
.setup-card[data-done]:focus-within :is(.setup-text, .setup-stage) {
	opacity: 1;
	filter: none;
}
@media (hover: hover) and (pointer: fine) {
	.setup-card[data-done]:hover .setup-overlay {
		opacity: 0;
		transform: scale(0.96);
		filter: blur(2px);
	}
	.setup-card[data-done]:hover :is(.setup-text, .setup-stage) {
		opacity: 1;
		filter: none;
	}
}
@media (prefers-reduced-motion: reduce) {
	.setup-card:active,
	.setup-overlay {
		transform: none;
	}
}
</style>
