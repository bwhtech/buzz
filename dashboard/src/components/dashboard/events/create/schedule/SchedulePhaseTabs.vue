<script setup lang="ts">
import { formatDateLabel, formatTime, type ScheduleDraft } from "./scheduleTime"
import type { Phase } from "./useScheduleRange"

// Two tabs that say which date the next tap sets. While the end is unpicked its tab says
// so and pulses, since a same-day organiser would otherwise never notice there is one.
defineProps<{ schedule: ScheduleDraft; awaitingEnd: boolean; endDateLabel: string }>()
const phase = defineModel<Phase>({ default: "start" })
</script>

<template>
	<div class="grid grid-cols-2 gap-2" role="tablist" :aria-label="__('Which date to pick')">
		<button
			type="button"
			role="tab"
			class="tab flex flex-col items-start gap-0.5 rounded-5 px-3 py-2 text-left"
			:aria-selected="phase === 'start'"
			@click="phase = 'start'"
		>
			<span class="text-xs font-medium text-ink-gray-5">{{ __("Starts") }}</span>
			<span class="text-base font-medium text-ink-gray-9">{{
				formatDateLabel(schedule.startDate)
			}}</span>
			<span class="text-xs tabular-nums text-ink-gray-5">{{ formatTime(schedule.startTime) }}</span>
		</button>
		<button
			type="button"
			role="tab"
			class="tab flex flex-col items-start gap-0.5 rounded-5 px-3 py-2 text-left"
			:class="awaitingEnd && 'awaiting'"
			:aria-selected="phase === 'end'"
			@click="phase = 'end'"
		>
			<span class="text-xs font-medium text-ink-gray-5">
				{{ __("Ends") }}
				<span v-if="awaitingEnd" class="text-ink-gray-7">· {{ __("pick a date") }}</span>
			</span>
			<span class="text-base font-medium text-ink-gray-9">{{ endDateLabel }}</span>
			<span class="text-xs tabular-nums text-ink-gray-5">{{ formatTime(schedule.endTime) }}</span>
		</button>
	</div>
</template>

<style scoped>
.tab {
	box-shadow: inset 0 0 0 1px var(--outline-gray-1);
	transition:
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 150ms ease,
		box-shadow 150ms ease;
}
.tab[aria-selected="true"] {
	background: var(--surface-gray-1);
	box-shadow: inset 0 0 0 1px var(--outline-gray-3);
}
.tab:active {
	transform: scale(0.98);
}
@media (hover: hover) and (pointer: fine) {
	.tab[aria-selected="false"]:hover {
		box-shadow: inset 0 0 0 1px var(--outline-gray-2);
	}
}
.awaiting {
	animation: ask 1.1s ease-out 2;
}
@keyframes ask {
	0% {
		outline: 0 solid var(--outline-gray-3);
	}
	70%,
	100% {
		outline: 4px solid transparent;
	}
}
@media (prefers-reduced-motion: reduce) {
	.tab {
		transition: none;
	}
	.awaiting {
		animation: none;
	}
}
</style>
