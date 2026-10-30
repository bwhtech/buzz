<script setup lang="ts">
import { computed } from "vue"

import { blockColors } from "./scheduleColors"
import { scheduleIcon } from "./scheduleIcons"
import { speakerLine, timeRange } from "./scheduleLayout"
import type { ScheduleItem } from "./scheduleTypes"
import { useBoard, useBuilder } from "./useScheduleBoard"

const props = defineProps<{
	item: ScheduleItem
	axis: "x" | "y"
	conflict?: string
	compact: boolean
	showSpeakers: boolean
	span: boolean
}>()

const builder = useBuilder()
const board = useBoard()

const details = computed(() => builder.itemDetails(props.item))
const colors = computed(() => blockColors(details.value.type?.color))
const icon = computed(() => scheduleIcon(details.value.type?.icon))
const selected = computed(() => board.selectedKey.value === props.item.key)
const speakers = computed(() => speakerLine(details.value.speakers))
const style = computed(() => ({
	background: colors.value.background,
	borderColor: props.conflict ? "var(--outline-red-3)" : colors.value.border,
	opacity: board.dragKey.value === props.item.key ? 0.35 : 1,
	pointerEvents: board.dragging.value ? ("none" as const) : ("auto" as const),
	boxShadow: selected.value ? "0 0 0 2px var(--outline-gray-9)" : "none",
	zIndex: selected.value ? 4 : props.span ? 1 : 2,
}))
const handle = computed(() =>
	props.axis === "y"
		? "inset-x-0 bottom-0 h-1.5 cursor-ns-resize"
		: "inset-y-0 right-0 w-1.5 cursor-ew-resize",
)
</script>

<template>
	<div
		draggable="true"
		:title="conflict || `${details.title} · ${timeRange(item)}`"
		class="absolute box-border flex cursor-grab flex-col gap-px overflow-hidden rounded-4 border transition-[box-shadow,opacity] duration-100"
		:class="[
			compact ? 'justify-center px-2' : 'justify-start px-2 py-1',
			span && 'items-center text-center',
		]"
		:style="style"
		@click.stop="board.select(item.key)"
		@dragstart="
			board.startDrag(
				{ kind: 'item', id: item.key, duration: item.duration, span, grabX: 0, grabY: 0 },
				$event,
			)
		"
		@dragend="board.endDrag"
	>
		<div class="flex min-w-0 max-w-full items-center gap-1.5">
			<span
				v-if="icon"
				:class="[icon, 'size-3.5 shrink-0']"
				:style="{ color: colors.meta }"
				aria-hidden="true"
			/>
			<div
				class="min-w-0 font-semibold"
				:class="
					compact
						? 'flex-auto truncate text-p-xs'
						: 'line-clamp-2 text-p-sm leading-tight [overflow-wrap:anywhere]'
				"
				:style="{ color: colors.title }"
			>
				{{ details.title }}
			</div>
			<span
				v-if="compact"
				class="min-w-0 shrink-[100] truncate text-p-xs tabular-nums"
				:style="{ color: colors.meta }"
			>
				{{ timeRange(item) }}
			</span>
			<span
				v-if="conflict"
				class="lucide-triangle-alert ml-auto size-3.5 shrink-0 text-ink-red-5"
				role="img"
				:aria-label="conflict"
			/>
		</div>
		<div v-if="!compact" class="truncate text-p-xs tabular-nums" :style="{ color: colors.meta }">
			{{ timeRange(item) }}
		</div>
		<div
			v-if="showSpeakers && speakers"
			class="mt-0.5 truncate text-p-xs"
			:style="{ color: colors.meta }"
		>
			{{ speakers }}
		</div>
		<div class="absolute" :class="handle" @mousedown="board.startResize(item.key, axis)($event)" />
	</div>
</template>
