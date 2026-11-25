<script setup lang="ts">
import type { StepEvent } from "../setupSteps"

// The venue search over a drawn street map. Set: the place and its pin; empty: the
// placeholder and a map with nothing on it.
defineProps<{ done: boolean; event: StepEvent }>()
</script>

<template>
	<div class="mini-panel overflow-hidden">
		<div class="space-y-2 p-2.5">
			<div class="grid grid-cols-2 rounded-[6px] bg-surface-gray-2 p-0.5 text-center">
				<span class="rounded-[5px] bg-surface-elevation-1 py-0.5 shadow-sm">Venue</span>
				<span class="mini-label py-0.5">Online</span>
			</div>
			<div class="mini-field">
				<span class="lucide-search size-3 text-ink-gray-5" />
				<span v-if="done" class="truncate">{{ event.venue }}</span>
				<span v-else class="mini-empty">Search a place</span>
			</div>
		</div>
		<svg viewBox="0 0 248 86" class="block w-full text-ink-gray-3" aria-hidden="true">
			<rect width="248" height="86" fill="var(--surface-gray-1)" />
			<g stroke="currentColor" fill="none" stroke-linecap="round">
				<path d="M-4 30 252 12M96-4l14 94M-4 70c60-6 120 0 170-18s60-6 86-8" stroke-width="5" />
				<path d="M40-4l10 94M190-4l-10 94M-4 50h256" stroke-width="2" />
			</g>
			<g v-if="done">
				<circle cx="124" cy="42" r="10" fill="var(--ink-gray-9)" opacity="0.08" />
				<circle
					cx="124"
					cy="42"
					r="4"
					fill="var(--ink-gray-9)"
					stroke="var(--surface-elevation-1)"
					stroke-width="2"
				/>
			</g>
		</svg>
	</div>
</template>
