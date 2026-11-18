<script setup lang="ts">
import { Button, Popover } from "frappe-ui"
import { ref, watch } from "vue"

import ScheduleCalendar from "./ScheduleCalendar.vue"
import SchedulePhaseTabs from "./SchedulePhaseTabs.vue"
import { type ScheduleDraft, formatDateLabel, today } from "./scheduleTime"
import TimeWheel from "./TimeWheel.vue"
import { quickDates, scheduleLabels, useScheduleRange } from "./useScheduleRange"

// One popover for the whole range: Starts / Ends tabs, quick dates, a month and two time
// wheels. It moves to Ends on its own once a start is picked.
const props = defineProps<{ schedule: ScheduleDraft; disabled?: boolean }>()

const open = ref(false)
const month = ref(props.schedule.startDate || today())
const range = useScheduleRange(props.schedule)
const { phase, awaitingEnd, sameDay, shownEnd, hovered, startTime, endTime } = range
const { endDateLabel, lengthLabel, summaryLine } = scheduleLabels(props.schedule)
const picks = quickDates()

watch(open, (isOpen) => {
	if (!isOpen) return range.finish()
	month.value = props.schedule.startDate || today()
	phase.value = "start"
})

const isPicked = (start: string, end: string) =>
	props.schedule.startDate === start && props.schedule.endDate === end
</script>

<template>
	<Popover v-model:open="open" :offset="6">
		<template #trigger>
			<button
				id="event-schedule-start"
				type="button"
				class="press flex min-h-14 w-full items-center gap-3 rounded-5 border border-outline-gray-2 bg-surface-white px-3.5 py-2 text-left aria-expanded:border-outline-gray-4 disabled:cursor-not-allowed disabled:opacity-60"
				:aria-expanded="open"
				:disabled="disabled"
			>
				<span class="lucide-calendar size-[18px] shrink-0 text-ink-gray-6" aria-hidden="true" />
				<span
					id="event-schedule-end"
					class="min-w-0 flex-1 truncate text-base font-medium text-ink-gray-9"
				>
					{{ summaryLine }}
				</span>
				<span class="shrink-0 text-xs text-ink-gray-5">{{ lengthLabel }}</span>
			</button>
		</template>

		<div class="flex w-[min(580px,calc(100vw-2rem))] flex-col gap-4 p-4">
			<SchedulePhaseTabs
				v-model="phase"
				:schedule="schedule"
				:awaiting-end="awaitingEnd"
				:end-date-label="endDateLabel"
			/>
			<div class="flex flex-wrap gap-1.5" role="group" :aria-label="__('Quick dates')">
				<button
					v-for="pick in picks"
					:key="pick.label"
					type="button"
					class="quick press inline-flex h-7 items-center gap-1.5 rounded-4 border px-3 text-sm"
					:aria-pressed="isPicked(pick.start, pick.end)"
					@click="range.pickQuick(pick.start, pick.end)"
				>
					<span class="font-medium">{{ pick.label }}</span>
					<span class="text-xs opacity-60">{{ pick.hint }}</span>
				</button>
			</div>
			<div
				class="grid grid-cols-2 gap-4 border-t border-outline-gray-1 pt-4 sm:grid-cols-[252px_minmax(0,1fr)_minmax(0,1fr)]"
			>
				<ScheduleCalendar
					v-model:month="month"
					class="col-span-2 sm:col-span-1"
					:start="schedule.startDate"
					:end="shownEnd"
					:min="phase === 'end' ? schedule.startDate : today()"
					@pick="range.pickDate"
					@hover="(date) => (hovered = date)"
				/>
				<TimeWheel
					v-model="startTime"
					:label="__('Start time')"
					class="sm:border-l sm:border-outline-gray-1 sm:pl-4"
				/>
				<TimeWheel
					v-model="endTime"
					:label="__('End time')"
					:after="sameDay ? schedule.startTime : undefined"
				/>
			</div>
			<div v-if="awaitingEnd" class="flex items-center gap-3 rounded-5 bg-surface-gray-1 px-3 py-2">
				<p class="flex-1 text-sm text-ink-gray-7">
					{{
						__("Ends on {0} unless you pick another date.", [formatDateLabel(schedule.startDate)])
					}}
				</p>
				<Button
					variant="subtle"
					size="sm"
					:label="__('Keep same day')"
					@click="range.keepSameDay"
				/>
			</div>
			<div class="flex justify-end">
				<Button variant="solid" :label="__('Done')" @click="open = false" />
			</div>
		</div>
	</Popover>
</template>

<style scoped>
.press {
	transition:
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 150ms ease,
		border-color 150ms ease;
}
.press:not(:disabled):active {
	transform: scale(0.98);
}
.quick {
	border-color: var(--outline-gray-2);
	background: var(--surface-white);
	color: var(--ink-gray-8);
}
.quick[aria-pressed="true"] {
	border-color: var(--outline-gray-3);
	background: var(--surface-gray-2);
	color: var(--ink-gray-9);
}
@media (hover: hover) and (pointer: fine) {
	.press:not(:disabled):hover:not([aria-expanded="true"]):not([aria-pressed="true"]) {
		background: var(--surface-gray-1);
	}
}
@media (prefers-reduced-motion: reduce) {
	.press:active {
		transform: none;
	}
}
</style>
