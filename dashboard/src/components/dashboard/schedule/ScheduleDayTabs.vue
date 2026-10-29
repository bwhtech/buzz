<script setup lang="ts">
import { Button, ContextMenu, dayjs } from "frappe-ui"
import { ref } from "vue"

import ScheduleDayDialog from "./ScheduleDayDialog.vue"
import type { ScheduleDay } from "./scheduleTypes"

const props = defineProps<{ days: ScheduleDay[]; counts: Record<string, number> }>()
const active = defineModel<string>({ required: true })
const emit = defineEmits<{
	add: []
	edit: [date: string, day: ScheduleDay]
	duplicate: [date: string]
	remove: [date: string]
}>()

const editing = ref<ScheduleDay | null>(null)
const dialogOpen = ref(false)

function menuFor(day: ScheduleDay) {
	return [
		{
			label: "Edit",
			icon: "lucide-pencil",
			onClick: () => {
				editing.value = day
				dialogOpen.value = true
			},
		},
		{ label: "Duplicate", icon: "lucide-copy", onClick: () => emit("duplicate", day.date) },
		{
			label: "Delete",
			icon: "lucide-trash-2",
			theme: "red" as const,
			disabled: props.days.length < 2,
			onClick: () => confirmRemove(day),
		},
	]
}

function confirmRemove(day: ScheduleDay) {
	const count = props.counts[day.date] ?? 0
	const message = count ? `Delete ${day.label} and its ${count} items?` : `Delete ${day.label}?`
	if (window.confirm(message)) emit("remove", day.date)
}

const subtitle = (day: ScheduleDay) => {
	const count = props.counts[day.date] ?? 0
	return `${dayjs(day.date).format("ddd D MMM")} · ${count} ${count === 1 ? "item" : "items"}`
}
</script>

<template>
	<div class="flex items-center gap-2 overflow-x-auto" role="tablist" aria-label="Schedule days">
		<ContextMenu v-for="day in days" :key="day.date" :options="menuFor(day)">
			<button
				type="button"
				role="tab"
				:aria-selected="active === day.date"
				class="flex min-w-36 shrink-0 flex-col items-start gap-0.5 rounded-5 border px-3.5 py-2 text-left transition-[background-color,border-color,transform] duration-150 ease-out active:scale-[0.97]"
				:class="
					active === day.date
						? 'border-outline-gray-3 bg-surface-white shadow-sm'
						: 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'
				"
				@click="active = day.date"
			>
				<span class="text-p-base font-semibold" :class="active === day.date && 'text-ink-gray-9'">
					{{ day.label || dayjs(day.date).format("ddd D MMM") }}
				</span>
				<span class="text-p-xs text-ink-gray-5">{{ subtitle(day) }}</span>
			</button>
		</ContextMenu>
		<Button variant="ghost" icon="lucide-plus" label="Add day" @click="emit('add')" />
		<ScheduleDayDialog
			v-model="dialogOpen"
			:day="editing"
			:taken="days.map((day) => day.date)"
			@save="(day) => editing && emit('edit', editing.date, day)"
		/>
	</div>
</template>
