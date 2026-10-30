<script setup lang="ts">
import { computed } from "vue"

import ScheduleAddRoom from "./ScheduleAddRoom.vue"
import ScheduleBlock from "./ScheduleBlock.vue"
import { HOUR_HEIGHT, hourLabel } from "./scheduleLayout"
import SchedulePlaceholder from "./SchedulePlaceholder.vue"
import ScheduleRoomHeader from "./ScheduleRoomHeader.vue"
import { useDayLayout } from "./useDayLayout"
import { pixelsPerMinute } from "./useScheduleBoard"

defineProps<{ timeZone?: string | null }>()

const TIME_COLUMN_WIDTH = 64
const ROOM_WIDTH = 220
const SIDE_COLUMN_WIDTH = 184
const minuteHeight = pixelsPerMinute("y")
const { board, rooms, roomIndex, visible, conflicts, lanes, countIn } = useDayLayout()

const count = computed(() => Math.max(rooms.value.length, 1))
const range = board.range
const height = computed(() => ((range.value.end - range.value.start) / 60) * HOUR_HEIGHT)
const hours = board.hours

function boxOf(item: (typeof visible.value)[number]) {
	const top = (item.start - range.value.start) * minuteHeight
	const length = item.duration * minuteHeight
	const span = !item.room
	const place = lanes.value[item.key] ?? { lane: 0, lanes: 1 }
	const column = roomIndex.value[item.room ?? ""] ?? 0
	return {
		span,
		compact: length < 44,
		showSpeakers: length >= 72,
		style: {
			top: `${top + 1}px`,
			height: `${Math.max(length - 2, 16)}px`,
			left: span
				? "4px"
				: `calc(${((column + place.lane / place.lanes) * 100) / count.value}% + 4px)`,
			width: span ? "calc(100% - 8px)" : `calc(${100 / count.value / place.lanes}% - 8px)`,
		},
	}
}

const placeholder = computed(() => {
	const current = board.placeholder.value
	if (!current || current.axis !== "y") return null
	if (!current.span && roomIndex.value[current.room ?? ""] === undefined && current.room)
		return null
	const left =
		current.span || !current.room
			? "4px"
			: `calc(${(roomIndex.value[current.room] * 100) / count.value}% + 4px)`
	const width =
		current.span || !current.room ? "calc(100% - 8px)" : `calc(${100 / count.value}% - 8px)`
	return {
		current,
		style: {
			top: `${(current.start - range.value.start) * minuteHeight + 1}px`,
			height: `${Math.max(current.duration * minuteHeight - 2, 18)}px`,
			left,
			width,
		},
	}
})
</script>

<template>
	<div class="relative h-full overflow-auto">
		<div
			class="relative"
			:style="{
				minWidth: `${TIME_COLUMN_WIDTH + rooms.length * ROOM_WIDTH + SIDE_COLUMN_WIDTH}px`,
			}"
		>
			<div class="sticky top-0 z-[8] flex border-b border-outline-gray-1 bg-surface-base">
				<div
					class="sticky left-0 z-[2] flex shrink-0 items-end justify-end bg-surface-base px-2.5 pb-2 text-[11px] text-ink-gray-4"
					:style="{ width: `${TIME_COLUMN_WIDTH}px` }"
				>
					{{ timeZone }}
				</div>
				<div class="flex min-w-0 flex-1">
					<ScheduleRoomHeader
						v-for="(room, index) in rooms"
						:key="room.name"
						class="min-w-0 flex-1 border-l border-outline-gray-1"
						:room="room"
						:index="index"
						:total="rooms.length"
						:count="countIn(room.name)"
					/>
				</div>
				<div
					class="flex shrink-0 items-center border-l border-outline-gray-1 p-2"
					:style="{ width: `${SIDE_COLUMN_WIDTH}px` }"
				>
					<ScheduleAddRoom />
				</div>
			</div>
			<div class="relative flex">
				<div
					class="sticky left-0 z-[6] shrink-0 bg-surface-base"
					:style="{ width: `${TIME_COLUMN_WIDTH}px`, height: `${height}px` }"
				>
					<span
						v-for="minute in hours"
						:key="minute"
						class="absolute right-2.5 whitespace-nowrap text-[11px] tabular-nums text-ink-gray-5"
						:style="{ top: `${Math.max(((minute - range.start) / 60) * HOUR_HEIGHT - 7, 2)}px` }"
					>
						{{ hourLabel(minute) }}
					</span>
				</div>
				<div class="relative min-w-0 flex-1" :style="{ height: `${height}px` }">
					<template v-for="minute in hours.slice(0, -1)" :key="minute">
						<div
							class="absolute inset-x-0 border-t border-outline-gray-1"
							:style="{ top: `${((minute - range.start) / 60) * HOUR_HEIGHT}px` }"
						/>
						<div
							class="absolute inset-x-0 border-t border-dashed border-outline-gray-1"
							:style="{ top: `${((minute - range.start) / 60) * HOUR_HEIGHT + HOUR_HEIGHT / 2}px` }"
						/>
					</template>
					<div class="absolute inset-0 flex">
						<div
							v-for="room in rooms"
							:key="room.name"
							class="min-w-0 flex-1 cursor-cell border-l border-outline-gray-1"
							@dragover="board.dragOver(room.name, 'y')($event)"
							@drop="board.dropOn(room.name)($event)"
							@click="board.clickSlot(room.name, 'y')($event)"
						/>
					</div>
					<div class="pointer-events-none absolute inset-0">
						<SchedulePlaceholder
							v-if="placeholder"
							:placeholder="placeholder.current"
							:style="placeholder.style"
						/>
						<ScheduleBlock
							v-for="item in visible"
							:key="item.key"
							:item="item"
							axis="y"
							:conflict="conflicts[item.key]"
							:compact="boxOf(item).compact"
							:show-speakers="boxOf(item).showSpeakers"
							:span="boxOf(item).span"
							:style="boxOf(item).style"
						/>
					</div>
				</div>
				<div
					class="shrink-0 border-l border-outline-gray-1 bg-surface-gray-1"
					:style="{ width: `${SIDE_COLUMN_WIDTH}px` }"
				/>
			</div>
		</div>
	</div>
</template>
