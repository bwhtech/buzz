<script setup lang="ts">
import { Button, ContextMenu, dayjs } from "frappe-ui"
import { ref } from "vue"

import ScheduleDayDialog from "./ScheduleDayDialog.vue"
import type { ScheduleDay } from "./scheduleTypes"
import { useBoard, useBuilder } from "./useScheduleBoard"

const builder = useBuilder()
const board = useBoard()
const editing = ref<ScheduleDay | null>(null)
const dialogOpen = ref(false)

const countOf = (date: string) => builder.dayItems(date).length
const dateLabel = (date: string) => dayjs(date).format("ddd D MMM")

function menuFor(day: ScheduleDay) {
	return [
		{
			label: "Edit",
			icon: "lucide-pencil",
			onClick: () => ((editing.value = day), (dialogOpen.value = true)),
		},
		{ label: "Duplicate", icon: "lucide-copy", onClick: () => builder.duplicateDay(day.date) },
		{
			label: "Delete",
			icon: "lucide-trash-2",
			theme: "red" as const,
			disabled: builder.days.value.length < 2,
			onClick: () => confirmRemove(day),
		},
	]
}

function confirmRemove(day: ScheduleDay) {
	const count = countOf(day.date)
	const message = count ? `Delete ${day.label} and its ${count} items?` : `Delete ${day.label}?`
	if (window.confirm(message)) builder.removeDay(day.date)
}

function pick(date: string) {
	builder.activeDate.value = date
	board.select(null)
}
</script>

<template>
	<div class="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Schedule days">
		<ContextMenu v-for="day in builder.days.value" :key="day.date" :options="menuFor(day)">
			<div
				role="tab"
				tabindex="0"
				:aria-selected="builder.activeDate.value === day.date"
				class="flex min-w-[132px] cursor-pointer select-none flex-col items-start gap-px rounded-5 border px-3 py-1.5 transition-colors duration-100"
				:class="
					board.dropDay.value === day.date
						? 'border-dashed border-outline-blue-3 bg-surface-blue-1'
						: builder.activeDate.value === day.date
							? 'border-outline-gray-2 bg-surface-base shadow-sm'
							: 'border-transparent bg-surface-gray-2'
				"
				@click="pick(day.date)"
				@keydown.enter="pick(day.date)"
				@dragover="board.dayOver(day.date)($event)"
				@drop="board.dayDrop(day.date)($event)"
				@dragleave="board.dayLeave($event)"
			>
				<span
					class="text-p-sm font-semibold"
					:class="builder.activeDate.value === day.date ? 'text-ink-gray-9' : 'text-ink-gray-7'"
				>
					{{ day.label || dateLabel(day.date) }}
				</span>
				<span class="whitespace-nowrap text-p-xs text-ink-gray-5">
					{{ dateLabel(day.date) }} · {{ countOf(day.date) }}
					{{ countOf(day.date) === 1 ? "item" : "items" }}
				</span>
			</div>
		</ContextMenu>
		<Button variant="ghost" icon="lucide-plus" label="Add day" @click="builder.addDay" />
		<ScheduleDayDialog
			v-model="dialogOpen"
			:day="editing"
			:taken="builder.days.value.map((day) => day.date)"
			@save="(day) => editing && builder.editDay(editing.date, day)"
		/>
	</div>
</template>
