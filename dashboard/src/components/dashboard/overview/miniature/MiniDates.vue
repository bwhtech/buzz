<script setup lang="ts">
import { dayjs } from "frappe-ui"

// Start and end fields over a month. Set: a two-day range; empty: TBA and no selection.
defineProps<{ done: boolean }>()

const start = dayjs().add(29, "day")
const first = start.startOf("month")
const days = Array.from({ length: 35 }, (_, index) => first.add(index - first.day(), "day"))
const TIMES = ["10:00", "18:00"]
const inRange = (day: typeof start) =>
	!day.isBefore(start, "day") && !day.isAfter(start.add(1, "day"), "day")
</script>

<template>
	<div class="mini-panel space-y-2 p-2.5">
		<div class="grid grid-cols-2 gap-1.5">
			<div v-for="(label, index) in ['Starts', 'Ends']" :key="label" class="space-y-1">
				<span class="mini-label">{{ label }}</span>
				<div class="mini-field">
					<span v-if="done" class="mini-value whitespace-nowrap text-ink-gray-8">
						{{ start.add(index, "day").format("D MMM") }}, {{ TIMES[index] }}
					</span>
					<span v-else class="mini-empty">TBA</span>
				</div>
			</div>
		</div>
		<div class="grid grid-cols-7 gap-y-0.5 text-center">
			<span v-for="day in 'SMTWTFS'" :key="day" class="mini-label text-[9px]">{{ day }}</span>
			<span
				v-for="day in days"
				:key="day.valueOf()"
				class="mini-day"
				:data-outside="day.month() !== first.month() || undefined"
				:data-picked="(done && inRange(day)) || undefined"
			>
				{{ day.date() }}
			</span>
		</div>
	</div>
</template>

<style scoped>
.mini-day {
	height: 16px;
	border-radius: 4px;
	font-size: 9.5px;
	line-height: 16px;
	color: var(--ink-gray-7);
	transition:
		background-color 200ms ease,
		color 200ms ease;
}
.mini-day[data-outside] {
	color: var(--ink-gray-3);
}
.mini-day[data-picked] {
	background: var(--ink-gray-9);
	color: var(--surface-elevation-1);
}
</style>
