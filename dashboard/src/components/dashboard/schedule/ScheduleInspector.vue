<script setup lang="ts">
import { Avatar, Badge, Button, FormControl, TextInput } from "frappe-ui"
import { computed } from "vue"

import { badgeStyle } from "./scheduleColors"
import { DURATIONS, SNAP_MINUTES, clock, durationLabel, timeRange } from "./scheduleLayout"
import type { ScheduleItem } from "./scheduleTypes"
import { useBoard, useBuilder } from "./useScheduleBoard"

const props = defineProps<{ item: ScheduleItem }>()
const builder = useBuilder()
const board = useBoard()

const details = computed(() => builder.itemDetails(props.item))
const conflict = computed(() => builder.conflictOf(props.item))
const range = computed(() => builder.rangeOf(props.item.date))
const isTalk = computed(() => !!props.item.talk)

const dayOptions = builder.dayOptions
const trackOptions = builder.trackOptions
const startOptions = computed(() => {
	const starts = new Set([props.item.start])
	for (let minute = range.value.start; minute <= range.value.end - 5; minute += SNAP_MINUTES)
		starts.add(minute)
	return [...starts]
		.toSorted((a, b) => a - b)
		.map((minute) => ({ label: clock(minute), value: String(minute) }))
})
const durationOptions = computed(() =>
	[...new Set([...DURATIONS, props.item.duration])]
		.toSorted((a, b) => a - b)
		.map((minutes) => ({ label: durationLabel(minutes), value: String(minutes) })),
)
const summary = computed(
	() =>
		`${timeRange(props.item)} · ${builder.dayLabel(props.item.date)} · ${builder.tracks.titleOf(props.item.track)}`,
)

const update = (patch: Partial<ScheduleItem>) => builder.update(props.item.key, patch)
const setTrack = (value: string) => update({ track: value === "all" ? null : value })
function remove() {
	builder.remove(props.item.key)
	board.select(null)
}
function duplicate() {
	const copy = builder.duplicate(props.item.key)
	if (copy) board.select(copy.key)
}
</script>

<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<div class="flex items-center gap-1.5 border-b border-outline-gray-1 py-2.5 pl-2 pr-2.5">
			<Button
				variant="ghost"
				icon="lucide-arrow-left"
				label="Back to library"
				@click="board.select(null)"
			/>
			<div class="flex-1 text-p-sm font-semibold text-ink-gray-9">Schedule item</div>
			<Button variant="ghost" icon="lucide-trash-2" label="Remove from schedule" @click="remove" />
		</div>
		<div class="flex flex-1 flex-col gap-4 overflow-auto p-4">
			<div class="flex flex-wrap gap-1.5">
				<Badge :label="details.type?.title ?? item.type" :style="badgeStyle(details.type?.color)" />
				<Badge v-if="isTalk" label="Accepted" theme="green" variant="outline" />
			</div>
			<div v-if="isTalk" class="flex flex-col gap-2.5">
				<div
					class="text-[17px] font-semibold leading-snug text-ink-gray-9 [overflow-wrap:anywhere]"
				>
					{{ details.title }}
				</div>
				<div
					v-for="name in details.speakers"
					:key="name"
					class="flex items-center gap-2 text-p-sm text-ink-gray-7"
				>
					<Avatar :label="name" size="sm" /><span>{{ name }}</span>
				</div>
			</div>
			<FormControl
				v-else
				label="Title"
				:model-value="item.title"
				@update:model-value="(value: string) => builder.retitle(item.key, value)"
			/>
			<div
				v-if="conflict"
				class="flex items-start gap-2 rounded-5 bg-surface-red-1 px-3 py-2.5 text-p-sm leading-snug text-ink-red-7"
			>
				<span class="lucide-triangle-alert mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
				<span>{{ conflict }}</span>
			</div>
			<div class="grid grid-cols-2 gap-3">
				<FormControl
					type="select"
					label="Day"
					:options="dayOptions"
					:model-value="item.date"
					@update:model-value="
						(value: string) => builder.place({ kind: 'item', id: item.key }, value)
					"
				/>
				<FormControl
					type="select"
					label="Track"
					:options="trackOptions"
					:model-value="item.track ?? 'all'"
					@update:model-value="setTrack"
				/>
				<FormControl
					type="select"
					label="Starts"
					:options="startOptions"
					:model-value="String(item.start)"
					@update:model-value="(value: string) => update({ start: Number(value) })"
				/>
				<FormControl
					type="select"
					label="Duration"
					:options="durationOptions"
					:model-value="String(item.duration)"
					@update:model-value="(value: string) => update({ duration: Number(value) })"
				/>
			</div>
			<div class="flex items-center gap-1.5 text-p-sm tabular-nums text-ink-gray-6">
				<span class="lucide-clock size-3.5 text-ink-gray-5" aria-hidden="true" /><span>{{
					summary
				}}</span>
			</div>
			<div class="flex flex-wrap gap-2 border-t border-outline-gray-1 pt-3">
				<Button variant="subtle" iconLeft="lucide-copy" label="Duplicate" @click="duplicate" />
				<Button
					variant="subtle"
					theme="red"
					:label="isTalk ? 'Unschedule talk' : 'Delete item'"
					@click="remove"
				/>
			</div>
			<p class="text-p-xs leading-normal text-ink-gray-5">
				Drag the edge of a block to change its length. Drag onto a day tab to move it to another
				day.
			</p>
		</div>
	</div>
</template>
