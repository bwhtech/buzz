<script setup lang="ts">
import type { StepEvent } from "../setupSteps"
import type { StepKey } from "../setupSteps"

import "./miniature.css"

import { MINIATURES } from "./miniatures"

// The screen each step opens, rebuilt small in real markup: greys only, 11px type,
// mono for values. Set steps show what was filled in; empty ones show the blank field.
defineProps<{ step: StepKey; done: boolean; event: StepEvent }>()
</script>

<template>
	<div class="miniature" :data-step="step" aria-hidden="true">
		<component :is="MINIATURES[step] as object" :done="done" :event="event" />
	</div>
</template>

<style scoped>
/* Each miniature keeps its drawn width and is zoomed in a little: it starts on the
   text's left edge and runs off the card's right and bottom, a crop of the screen
   rather than a shrunken copy of it. The event page is the exception: narrow, so it
   sits whole in the middle. */
.miniature {
	position: relative;
	width: 100%;
	height: 100%;
	font-size: 11px;
	line-height: 16px;
	color: var(--ink-gray-8);
}
.miniature > :deep(*) {
	position: absolute;
	top: 4px;
	left: 20px;
	width: 248px;
	scale: 0.94;
	transform-origin: top left;
	transition: transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.miniature[data-step="page"] > :deep(*) {
	left: 50%;
	width: 196px;
	scale: 1;
	translate: -50% 0;
	transform-origin: top center;
}
:global(.setup-card:is(:hover, :focus-within)) .miniature > :deep(*) {
	transform: translateY(-2px);
}
@media (prefers-reduced-motion: reduce) {
	:global(.setup-card:is(:hover, :focus-within)) .miniature > :deep(*) {
		transform: none;
	}
}
</style>
