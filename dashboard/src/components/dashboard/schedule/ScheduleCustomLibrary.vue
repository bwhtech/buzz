<script setup lang="ts">
import { Button, FormControl } from "frappe-ui"
import { computed, ref } from "vue"

import { scheduleIcon } from "./scheduleIcons"
import { DURATIONS, TALK_TYPES, durationLabel } from "./scheduleLayout"
import { useBoard, useBuilder } from "./useScheduleBoard"

const builder = useBuilder()
const board = useBoard()

const templates = computed(() =>
	builder.types.value
		.filter((type) => !TALK_TYPES.has(type.name))
		.map((type) => ({ ...type, label: type.name === "Custom" ? "Untitled item" : type.title })),
)
const meta = (type: (typeof templates.value)[number]) =>
	`${type.default_duration} min${type.spans_all_tracks ? " · All tracks" : ""}`

const title = ref("")
const duration = ref("30")
const room = ref("all")
const durationOptions = DURATIONS.map((minutes) => ({
	label: durationLabel(minutes),
	value: String(minutes),
}))
const roomOptions = computed(() => [
	{ label: "All tracks", value: "all" },
	...builder.rooms.rooms.value.map((entry) => ({ label: entry.title, value: entry.name })),
])
const addLabel = computed(() => `Add to ${builder.activeDay.value?.label ?? "day"}`)

function drag(type: (typeof templates.value)[number], event: DragEvent) {
	const payload = {
		kind: "type" as const,
		id: type.name,
		duration: type.default_duration,
		span: !!type.spans_all_tracks,
		grabX: 0,
		grabY: 0,
	}
	board.startDrag(payload, event)
}

function addTemplate(name: string) {
	const item = builder.place({ kind: "type", id: name }, builder.activeDate.value)
	if (item && item.type === "Custom") board.select(item.key)
}

function addCustom() {
	builder.addCustom(
		builder.activeDate.value,
		title.value,
		Number(duration.value),
		room.value === "all" ? null : room.value,
	)
	title.value = ""
}
</script>

<template>
	<div class="flex min-h-0 flex-1 flex-col gap-3.5 overflow-auto px-3 pb-4 pt-1">
		<p class="px-0.5 pt-1 text-p-xs text-ink-gray-5">
			Drag a template, or click to add it at the next free slot
		</p>
		<div class="grid grid-cols-2 gap-2">
			<button
				v-for="type in templates"
				:key="type.name"
				type="button"
				draggable="true"
				class="flex cursor-grab flex-col gap-2 rounded-5 border border-outline-gray-2 bg-surface-base p-2.5 text-left transition-[box-shadow,border-color] hover:border-outline-gray-3 hover:shadow-sm"
				@dragstart="drag(type, $event)"
				@dragend="board.endDrag"
				@click="addTemplate(type.name)"
			>
				<span
					class="flex size-7 items-center justify-center rounded-4 bg-surface-gray-2 text-ink-gray-7"
				>
					<span :class="[scheduleIcon(type.icon), 'size-4']" aria-hidden="true" />
				</span>
				<span>
					<span class="block text-p-sm font-semibold text-ink-gray-9">{{ type.label }}</span>
					<span class="block text-p-xs text-ink-gray-5">{{ meta(type) }}</span>
				</span>
			</button>
		</div>
		<div class="flex flex-col gap-2.5 border-t border-outline-gray-1 pt-3.5">
			<div class="text-p-sm font-semibold text-ink-gray-9">Create your own</div>
			<FormControl
				v-model="title"
				label="Title"
				placeholder="Sponsor demo, group photo…"
				autocomplete="off"
			/>
			<div class="grid grid-cols-2 gap-2.5">
				<FormControl v-model="duration" type="select" label="Duration" :options="durationOptions" />
				<FormControl v-model="room" type="select" label="Track" :options="roomOptions" />
			</div>
			<Button variant="solid" :label="addLabel" class="w-full" @click="addCustom" />
		</div>
	</div>
</template>
