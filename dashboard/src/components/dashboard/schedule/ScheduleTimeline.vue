<script setup lang="ts">
import { computed } from "vue"

import ScheduleAddRoom from "./ScheduleAddRoom.vue"
import ScheduleBlock from "./ScheduleBlock.vue"
import ScheduleGhost from "./ScheduleGhost.vue"
import { ROW_HEIGHT, hourLabel } from "./scheduleLayout"
import ScheduleRoomHeader from "./ScheduleRoomHeader.vue"
import { useDayLayout } from "./useDayLayout"
import { pixelsPerMinute } from "./useScheduleBoard"

const LABELS = 200
const AXIS = 36
const pxm = pixelsPerMinute("x")
const { board, rooms, roomIndex, visible, conflicts, lanes, countIn } = useDayLayout()

const range = board.range
const width = computed(() => (range.value.end - range.value.start) * pxm)
const rowsHeight = computed(() => rooms.value.length * ROW_HEIGHT)
const hours = computed(() => {
	const list = []
	for (let minute = range.value.start; minute <= range.value.end; minute += 60) list.push(minute)
	return list
})
const left = (minute: number) => (minute - range.value.start) * pxm

function boxOf(item: (typeof visible.value)[number]) {
	const span = !item.room
	const length = item.duration * pxm
	const place = lanes.value[item.key] ?? { lane: 0, lanes: 1 }
	const laneHeight = (ROW_HEIGHT - 16) / place.lanes
	const compact = !span && (laneHeight < 44 || length < 96)
	const row = roomIndex.value[item.room ?? ""] ?? 0
	const style = span
		? {
				top: "4px",
				height: `${Math.max(rowsHeight.value - 8, 40)}px`,
				left: `${left(item.start) + 1}px`,
				width: `${Math.max(length - 2, 12)}px`,
				paddingTop: "8px",
			}
		: {
				top: `${row * ROW_HEIGHT + 8 + place.lane * laneHeight}px`,
				height: `${laneHeight - 2}px`,
				left: `${left(item.start) + 1}px`,
				width: `${Math.max(length - 2, 12)}px`,
			}
	return { span, compact, showSpeakers: !compact && !span && laneHeight >= 62, style }
}

const ghost = computed(() => {
	const current = board.ghost.value
	if (!current || current.axis !== "x") return null
	const row = roomIndex.value[current.room ?? ""]
	if (row === undefined && !current.span) return null
	const style = {
		left: `${left(current.start) + 1}px`,
		width: `${current.duration * pxm - 2}px`,
		top: current.span ? "4px" : `${row * ROW_HEIGHT + 8}px`,
		height: current.span ? `${rowsHeight.value - 8}px` : `${ROW_HEIGHT - 18}px`,
	}
	return { current, style }
})
</script>

<template>
	<div class="relative h-full overflow-auto">
		<div class="relative min-w-full" :style="{ width: `${LABELS + width}px` }">
			<div
				class="sticky top-0 z-[8] flex border-b border-outline-gray-1 bg-surface-base"
				:style="{ height: `${AXIS}px` }"
			>
				<div
					class="sticky left-0 z-[2] flex shrink-0 items-center border-r border-outline-gray-1 bg-surface-base px-4 text-p-xs text-ink-gray-5"
					:style="{ width: `${LABELS}px` }"
				>
					Rooms
				</div>
				<div class="relative shrink-0" :style="{ width: `${width}px` }">
					<span
						v-for="minute in hours"
						:key="minute"
						class="absolute top-2.5 whitespace-nowrap text-[11px] tabular-nums text-ink-gray-5"
						:style="{ left: `${left(minute) + 6}px` }"
					>
						{{ hourLabel(minute) }}
					</span>
				</div>
			</div>
			<div class="relative">
				<div
					class="pointer-events-none absolute top-0"
					:style="{ left: `${LABELS}px`, width: `${width}px`, height: `${rowsHeight}px` }"
				>
					<template v-for="minute in hours.slice(0, -1)" :key="minute">
						<div
							class="absolute inset-y-0 border-l border-outline-gray-1"
							:style="{ left: `${left(minute)}px` }"
						/>
						<div
							class="absolute inset-y-0 border-l border-dashed border-outline-gray-1"
							:style="{ left: `${left(minute + 30)}px` }"
						/>
					</template>
				</div>
				<div
					v-for="(room, index) in rooms"
					:key="room.name"
					class="box-border flex border-b border-outline-gray-1"
					:style="{ height: `${ROW_HEIGHT}px` }"
				>
					<div
						class="sticky left-0 z-[6] shrink-0 border-r border-outline-gray-1 bg-surface-base"
						:style="{ width: `${LABELS}px` }"
					>
						<ScheduleRoomHeader
							class="h-full"
							:room="room"
							:index="index"
							:total="rooms.length"
							:count="countIn(room.name)"
						/>
					</div>
					<div
						class="relative z-[1] shrink-0 cursor-cell"
						:style="{ width: `${width}px` }"
						@dragover="board.dragOver(room.name, 'x')($event)"
						@drop="board.dropOn(room.name)($event)"
						@click="board.clickSlot(room.name, 'x')($event)"
					/>
				</div>
				<div
					class="pointer-events-none absolute top-0 z-[3]"
					:style="{ left: `${LABELS}px`, width: `${width}px`, height: `${rowsHeight}px` }"
				>
					<ScheduleGhost v-if="ghost" :ghost="ghost.current" :style="ghost.style" />
					<ScheduleBlock
						v-for="item in visible"
						:key="item.key"
						:item="item"
						axis="x"
						:conflict="conflicts[item.key]"
						:compact="boxOf(item).compact"
						:show-speakers="boxOf(item).showSpeakers"
						:span="boxOf(item).span"
						:style="boxOf(item).style"
					/>
				</div>
			</div>
			<div class="sticky left-0 p-2.5" :style="{ width: `${LABELS}px` }">
				<ScheduleAddRoom />
			</div>
		</div>
	</div>
</template>
