<script setup lang="ts">
import { computed } from "vue"

import ScheduleGhost from "../ScheduleGhost.vue"
import { hourLabel, lanesOf, SNAP_MINUTES } from "../scheduleLayout"
import type { ScheduleItem } from "../scheduleTypes"
import { useDayLayout } from "../useDayLayout"
import ScheduleMobileBlock from "./ScheduleMobileBlock.vue"
import ScheduleMobileCard from "./ScheduleMobileCard.vue"
import { useMobile } from "./useScheduleMobile"
import { useScheduleTouchDrag } from "./useScheduleTouchDrag"

const PIXELS_PER_MINUTE = 1.5
const RAIL = 48
const COLUMN = 150
const MIN_BLOCK = 14
const GRID_PADDING = 10
const GHOST_MINUTES = 30

const { builder, board, rooms, dayItems, conflicts } = useDayLayout()
const mobile = useMobile()
const isGrid = computed(() => mobile.view.value === "grid")
const columnWidth = computed(() => (isGrid.value ? COLUMN : null))
const touch = useScheduleTouchDrag(PIXELS_PER_MINUTE, columnWidth)

const range = board.range
const height = computed(() => (range.value.end - range.value.start) * PIXELS_PER_MINUTE)
const hours = computed(() => {
	const list = []
	for (let minute = range.value.start; minute <= range.value.end; minute += 60) list.push(minute)
	return list
})

const shownRooms = computed(() =>
	isGrid.value ? rooms.value : rooms.value.filter((room) => room.name === mobile.activeRoom.value),
)
const displayed = computed(() =>
	dayItems.value.map((item) =>
		touch.position.value?.key === item.key ? { ...item, ...touch.position.value } : item,
	),
)
const spans = computed(() => displayed.value.filter((item) => !item.room))
const columns = computed(() =>
	shownRooms.value.map((room) => {
		const items = displayed.value.filter((item) => item.room === room.name)
		const lanes = lanesOf(items)
		return { room, items: items.map((item) => ({ item, ...lanes[item.key] })) }
	}),
)

const top = (start: number) => (start - range.value.start) * PIXELS_PER_MINUTE + 1
const lengthOf = (item: ScheduleItem) => Math.max(item.duration * PIXELS_PER_MINUTE - 2, MIN_BLOCK)

function blockStyle(item: ScheduleItem, lane: number, lanes: number) {
	return {
		top: `${top(item.start)}px`,
		height: `${lengthOf(item)}px`,
		left: `calc(${(lane / lanes) * 100}% + 3px)`,
		width: `calc(${100 / lanes}% - 6px)`,
	}
}

function tapSlot(event: MouseEvent, room: string) {
	if (event.target !== event.currentTarget) return
	const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
	const raw = range.value.start + (event.clientY - box.top) / PIXELS_PER_MINUTE
	const start = Math.floor(raw / SNAP_MINUTES) * SNAP_MINUTES
	mobile.openAdd(Math.min(start, range.value.end - SNAP_MINUTES), room)
}

const spanStyle = (item: ScheduleItem) => ({
	left: `${RAIL + 3}px`,
	right: "3px",
	top: `${GRID_PADDING + top(item.start)}px`,
	height: `${lengthOf(item)}px`,
})
const ghostStyle = (start: number) => ({
	top: `${top(start)}px`,
	height: `${GHOST_MINUTES * PIXELS_PER_MINUTE - 2}px`,
})

const sheet = mobile.sheet
const ghostFor = (room: string) =>
	sheet.value?.type === "add" && sheet.value.room === room
		? { room, start: sheet.value.start, duration: GHOST_MINUTES, axis: "y" as const, span: false }
		: null
const gridLines = computed(() => {
	const hour = 60 * PIXELS_PER_MINUTE
	return `repeating-linear-gradient(to bottom, var(--outline-gray-1) 0 1px, transparent 1px ${hour}px)`
})
const empty = computed(() => !dayItems.value.length && !sheet.value)
</script>

<template>
	<div class="relative min-h-0 flex-1">
		<div class="h-full overflow-auto overscroll-contain">
			<div :style="{ minWidth: `${RAIL + (isGrid ? COLUMN * columns.length : 0)}px` }">
				<div
					v-if="isGrid"
					class="sticky top-0 z-[6] flex border-b border-outline-gray-1 bg-surface-base"
				>
					<div
						class="sticky left-0 z-[1] shrink-0 bg-surface-base"
						:style="{ width: `${RAIL}px` }"
					/>
					<div
						v-for="column in columns"
						:key="column.room.name"
						class="box-border flex min-w-0 shrink-0 gap-1.5 border-l border-outline-gray-1 p-2.5 text-p-xs font-semibold text-ink-gray-8"
						:style="{ width: `${COLUMN}px` }"
					>
						<span class="truncate">{{ column.room.title }}</span>
						<span class="shrink-0 font-normal text-ink-gray-5">{{
							column.items.length || ""
						}}</span>
					</div>
				</div>
				<div class="relative flex pb-40" :style="{ paddingTop: `${GRID_PADDING}px` }">
					<div
						class="sticky left-0 z-[4] shrink-0 bg-surface-base"
						:style="{ width: `${RAIL}px`, height: `${height}px` }"
					>
						<span
							v-for="minute in hours"
							:key="minute"
							class="absolute right-2 -translate-y-1/2 bg-surface-base px-0.5 text-[11px] tabular-nums text-ink-gray-5"
							:style="{ top: `${(minute - range.start) * PIXELS_PER_MINUTE}px` }"
							>{{ hourLabel(minute) }}</span
						>
					</div>
					<div
						v-for="column in columns"
						:key="column.room.name"
						class="relative box-border cursor-pointer border-l border-outline-gray-1"
						:class="isGrid ? 'shrink-0' : 'min-w-0 flex-1'"
						:style="{
							height: `${height}px`,
							width: isGrid ? `${COLUMN}px` : undefined,
							backgroundImage: gridLines,
						}"
						@click="tapSlot($event, column.room.name)"
					>
						<ScheduleGhost
							v-if="ghostFor(column.room.name)"
							class="inset-x-[3px]"
							:ghost="ghostFor(column.room.name)!"
							:style="ghostStyle(ghostFor(column.room.name)!.start)"
						/>
						<ScheduleMobileBlock
							v-for="entry in column.items"
							:key="entry.item.key"
							:item="entry.item"
							:height="lengthOf(entry.item)"
							:conflict="conflicts[entry.item.key]"
							:dragging="touch.position.value?.key === entry.item.key"
							:style="blockStyle(entry.item, entry.lane, entry.lanes)"
							@press="(event, mode) => touch.begin(event, entry.item, mode)"
							@open="mobile.openEdit(entry.item.key)"
						/>
					</div>
					<ScheduleMobileCard
						v-for="item in spans"
						:key="item.key"
						:item="item"
						:conflict="conflicts[item.key]"
						class="absolute z-[3] !w-auto !py-0"
						:style="spanStyle(item)"
						@click.stop="mobile.openEdit(item.key)"
					/>
				</div>
			</div>
		</div>
		<div
			v-if="empty"
			class="pointer-events-none absolute left-1/2 top-24 z-[8] -translate-x-1/2 whitespace-nowrap rounded-full bg-surface-base px-3.5 py-2 text-p-sm text-ink-gray-7 shadow-lg"
		>
			Tap an empty slot to add a session
		</div>
	</div>
</template>
