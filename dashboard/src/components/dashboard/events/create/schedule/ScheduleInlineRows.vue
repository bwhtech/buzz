<script setup lang="ts">
import { dayjsLocal } from "frappe-ui"
import { computed, ref } from "vue"

import ScheduleCalendar from "./ScheduleCalendar.vue"
import { type ScheduleDraft, formatTime, today } from "./scheduleTime"
import TimeWheelColumns from "./TimeWheelColumns.vue"
import { useScheduleEdits } from "./useScheduleRange"

// The phone schedule: Starts and Ends rows, each with a date chip and a time chip. A chip
// opens its calendar or wheels right under its row, one at a time, so nothing covers the
// form and a same-day event never asks for an end date.
const props = defineProps<{ schedule: ScheduleDraft; disabled?: boolean }>()
const edits = useScheduleEdits(props.schedule)
const { startTime, endTime } = edits

type Panel = "" | "startDate" | "startTime" | "endDate" | "endTime"
const openPanel = ref<Panel>("")
const month = ref(props.schedule.startDate)

function toggle(panel: Panel) {
	openPanel.value = openPanel.value === panel ? "" : panel
	month.value = panel === "endDate" ? props.schedule.endDate : props.schedule.startDate
}

function pickStartDate(date: string) {
	edits.moveStart({ date })
	openPanel.value = ""
}

function pickEndDate(date: string) {
	props.schedule.endDate = date
	edits.ensureEndAfterStart()
	openPanel.value = ""
}

const rows = computed(() => [
	{
		key: "start",
		label: __("Starts"),
		date: props.schedule.startDate,
		time: props.schedule.startTime,
	},
	{ key: "end", label: __("Ends"), date: props.schedule.endDate, time: props.schedule.endTime },
])

const dateLabel = (row: { key: string; date: string }) =>
	row.key === "end" && row.date === props.schedule.startDate
		? __("Same day")
		: dayjsLocal(row.date).format("D MMM YYYY")
</script>

<template>
	<div
		id="event-schedule-start"
		class="overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-base"
	>
		<template v-for="(row, index) in rows" :key="row.key">
			<div
				class="flex min-h-12 items-center gap-2 px-3.5"
				:class="index && 'border-t border-outline-gray-1'"
			>
				<span class="flex-1 text-base text-ink-gray-9">{{ row.label }}</span>
				<button
					type="button"
					class="chip h-8 w-[8.5rem] rounded-4 text-center text-base tabular-nums"
					:aria-expanded="openPanel === `${row.key}Date`"
					:disabled="disabled"
					@click="toggle(`${row.key}Date` as Panel)"
				>
					{{ dateLabel(row) }}
				</button>
				<button
					:id="row.key === 'end' ? 'event-schedule-end' : undefined"
					type="button"
					class="chip h-8 w-[6.5rem] rounded-4 text-center text-base tabular-nums"
					:aria-expanded="openPanel === `${row.key}Time`"
					:disabled="disabled"
					@click="toggle(`${row.key}Time` as Panel)"
				>
					{{ formatTime(row.time) }}
				</button>
			</div>
			<div class="expand grid" :data-open="openPanel.startsWith(row.key) || undefined">
				<div class="min-h-0 overflow-hidden">
					<div class="px-3.5 pb-3">
						<ScheduleCalendar
							v-if="openPanel === `${row.key}Date`"
							v-model:month="month"
							:start="schedule.startDate"
							:end="schedule.endDate"
							:min="row.key === 'end' ? schedule.startDate : today()"
							@pick="row.key === 'start' ? pickStartDate($event) : pickEndDate($event)"
						/>
						<TimeWheelColumns
							v-if="openPanel === 'startTime' && row.key === 'start'"
							v-model="startTime"
						/>
						<TimeWheelColumns
							v-if="openPanel === 'endTime' && row.key === 'end'"
							v-model="endTime"
						/>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>

<style scoped>
.chip {
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
	transition:
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 150ms ease;
}
.chip[aria-expanded="true"] {
	background: var(--surface-gray-3);
	color: var(--ink-gray-9);
}
.chip:not(:disabled):active {
	transform: scale(0.97);
}
.chip:disabled {
	opacity: 0.6;
}
.expand {
	grid-template-rows: 0fr;
	transition: grid-template-rows 240ms cubic-bezier(0.23, 1, 0.32, 1);
}
.expand[data-open] {
	grid-template-rows: 1fr;
}
@media (prefers-reduced-motion: reduce) {
	.chip,
	.expand {
		transition: none;
	}
}
</style>
