<script setup lang="ts">
import { computed } from "vue"

import { blockColors } from "../scheduleColors"
import { clock } from "../scheduleLayout"
import type { ScheduleItem } from "../scheduleTypes"
import { useBuilder } from "../useScheduleBoard"
import type { DragMode } from "./useScheduleTouchDrag"

const LINE_HEIGHT = 16
const props = defineProps<{
	item: ScheduleItem
	height: number
	conflict?: string
	dragging: boolean
}>()
const emit = defineEmits<{ press: [event: PointerEvent, mode: DragMode]; open: [] }>()
const builder = useBuilder()

const resolved = computed(() => builder.resolve(props.item))
const colors = computed(() => blockColors(resolved.value.type?.color))
const showMeta = computed(() => props.height > 44)
const showHandle = computed(() => props.height > 30)
const lines = computed(() =>
	Math.max(1, Math.floor((props.height - (showMeta.value ? 24 : 8)) / LINE_HEIGHT)),
)
const meta = computed(() => {
	const range = `${clock(props.item.start)}–${clock(props.item.start + props.item.duration)}`
	const speaker = resolved.value.speakers[0]
	return speaker ? `${range} · ${speaker}` : range
})
const titleStyle = computed(() => ({
	display: "-webkit-box",
	WebkitBoxOrient: "vertical" as const,
	WebkitLineClamp: lines.value,
	overflow: "hidden",
}))
const style = computed(() => ({
	background: colors.value.background,
	borderColor: props.conflict ? "var(--outline-red-3)" : colors.value.border,
	padding: showHandle.value ? "5px 28px 5px 8px" : "1px 8px",
}))
</script>

<template>
	<div
		class="absolute box-border select-none overflow-hidden rounded-5 border transition-shadow"
		:class="dragging ? 'z-10 scale-[1.02] opacity-95 shadow-xl' : 'z-[1]'"
		:style="style"
		@click.stop="emit('open')"
	>
		<div
			class="text-p-xs font-medium leading-4 text-ink-gray-9 [overflow-wrap:anywhere]"
			:style="titleStyle"
		>
			{{ resolved.title }}
		</div>
		<div v-if="showMeta" class="mt-0.5 truncate text-[11px] tabular-nums text-ink-gray-6">
			{{ meta }}
		</div>
		<span
			v-if="conflict"
			class="absolute right-[30px] top-[5px] size-[7px] rounded-full bg-surface-red-6"
			role="img"
			:aria-label="conflict"
		/>
		<div
			v-if="showHandle"
			class="absolute inset-y-0 right-0 flex w-7 touch-none items-center justify-center text-ink-gray-5"
			aria-label="Drag to move"
			@pointerdown="emit('press', $event, 'move')"
			@click.stop
		>
			<span class="lucide-grip-vertical size-4" aria-hidden="true" />
		</div>
		<div
			v-if="showHandle"
			class="absolute inset-x-0 -bottom-0.5 flex h-4 touch-none items-center justify-center"
			@pointerdown="emit('press', $event, 'resize')"
			@click.stop
		>
			<div class="h-1 w-6 rounded-sm bg-surface-gray-7" />
		</div>
	</div>
</template>
