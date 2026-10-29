<script setup lang="ts">
import { computed } from "vue"

import ScheduleItemBlock from "./ScheduleItemBlock.vue"
import { SNAP_MINUTES, endMinutes, placeInLanes, snap, startMinutes } from "./scheduleTime"
import { DRAG_TYPE, type ScheduleItem, type ScheduleItemType } from "./scheduleTypes"

const props = defineProps<{
	items: ScheduleItem[]
	types: Record<string, ScheduleItemType>
	conflicts: Set<string>
	vertical: boolean
	pixelsPerMinute: number
	rangeStart: number
}>()
const emit = defineEmits<{
	select: [key: string]
	create: [minute: number]
	drop: [minute: number, payload: string]
}>()

const placed = computed(() => placeInLanes(props.items))
const GAP = 2

function styleOf({ item, lane, lanes }: ReturnType<typeof placeInLanes>[number]) {
	const offset = (startMinutes(item) - props.rangeStart) * props.pixelsPerMinute
	const length = (endMinutes(item) - startMinutes(item)) * props.pixelsPerMinute - GAP
	const across = `${(lane / lanes) * 100}%`
	const thickness = `calc(${100 / lanes}% - ${GAP}px)`
	return props.vertical
		? { top: `${offset}px`, height: `${length}px`, left: across, width: thickness }
		: { left: `${offset}px`, width: `${length}px`, top: across, height: thickness }
}

const lineSize = computed(() => `${60 * props.pixelsPerMinute}px`)
const gridStyle = computed(() => {
	const direction = props.vertical ? "to bottom" : "to right"
	const half = (60 * props.pixelsPerMinute) / 2
	return {
		backgroundImage: [
			`repeating-linear-gradient(${direction}, var(--outline-gray-2) 0 1px, transparent 1px ${lineSize.value})`,
			`repeating-linear-gradient(${direction}, transparent 0 ${half}px, var(--outline-gray-1) ${half}px ${half + 1}px, transparent ${half + 1}px ${lineSize.value})`,
		].join(","),
	}
})

function minuteAt(event: MouseEvent | DragEvent) {
	const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
	const distance = props.vertical ? event.clientY - rect.top : event.clientX - rect.left
	return Math.max(0, snap(props.rangeStart + distance / props.pixelsPerMinute - SNAP_MINUTES / 2))
}

function onDrop(event: DragEvent) {
	const payload = event.dataTransfer?.getData(DRAG_TYPE)
	if (payload) emit("drop", minuteAt(event), payload)
}
</script>

<template>
	<div
		class="relative size-full"
		:style="gridStyle"
		@dblclick.self="emit('create', minuteAt($event))"
		@dragover.prevent="$event.dataTransfer && ($event.dataTransfer.dropEffect = 'copy')"
		@drop.prevent="onDrop"
	>
		<div v-for="entry in placed" :key="entry.item.key" class="absolute" :style="styleOf(entry)">
			<ScheduleItemBlock
				:item="entry.item"
				:type="types[entry.item.type]"
				:conflict="conflicts.has(entry.item.key)"
				@select="emit('select', entry.item.key)"
			/>
		</div>
	</div>
</template>
