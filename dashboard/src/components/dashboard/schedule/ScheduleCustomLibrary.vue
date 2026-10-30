<script setup lang="ts">
import { blockColors } from "./scheduleColors"
import { scheduleIcon } from "./scheduleIcons"
import { durationLabel } from "./scheduleLayout"
import { useBoard, useBuilder } from "./useScheduleBoard"

const builder = useBuilder()
const board = useBoard()

const types = builder.itemTypes

function drag(type: (typeof types.value)[number], event: DragEvent) {
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
</script>

<template>
	<div class="flex min-h-0 basis-2/5 flex-col border-t border-outline-gray-1">
		<div class="px-3.5 py-2.5">
			<span class="text-p-xs text-ink-gray-5">Breaks and other items</span>
		</div>
		<div class="flex min-h-0 flex-1 flex-col gap-1 overflow-auto px-3 pb-3">
			<button
				v-for="type in types"
				:key="type.name"
				type="button"
				draggable="true"
				class="flex h-8 shrink-0 cursor-grab items-center gap-2 rounded-4 border px-2.5 text-left transition-shadow hover:shadow-sm"
				:style="{
					background: blockColors(type.color).background,
					borderColor: blockColors(type.color).border,
				}"
				@dragstart="drag(type, $event)"
				@dragend="board.endDrag"
				@click="board.addItem(type.name)"
			>
				<span
					:class="[scheduleIcon(type.icon), 'size-4 shrink-0']"
					:style="{ color: blockColors(type.color).meta }"
					aria-hidden="true"
				/>
				<span
					class="min-w-0 flex-1 truncate text-p-sm font-medium"
					:style="{ color: blockColors(type.color).title }"
					>{{ type.name === "Custom" ? "Untitled item" : type.title }}</span
				>
				<span class="shrink-0 text-p-xs" :style="{ color: blockColors(type.color).meta }">{{
					durationLabel(type.default_duration)
				}}</span>
			</button>
		</div>
	</div>
</template>
