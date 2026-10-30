<script setup lang="ts">
import { useElementSize } from "@vueuse/core"
import { computed, ref } from "vue"

import { hourLabel, lanesOf, SNAP_MINUTES } from "../scheduleLayout"
import SchedulePlaceholder from "../SchedulePlaceholder.vue"
import type { ScheduleItem } from "../scheduleTypes"
import { useDayLayout } from "../useDayLayout"
import ScheduleMobileBlock from "./ScheduleMobileBlock.vue"
import { useMobile } from "./useScheduleMobile"
import { useScheduleTouchDrag } from "./useScheduleTouchDrag"

const PIXELS_PER_MINUTE = 1.5
const TIME_COLUMN_WIDTH = 48
const COLUMN_PEEK = 28
const MIN_COLUMN = 180
const HEADER_HEIGHT = 40
const MIN_BLOCK = 14
const GRID_PADDING = 10
const PLACEHOLDER_MINUTES = 30

const { builder, board, rooms, dayItems, conflicts } = useDayLayout()
const mobile = useMobile()
const isGrid = computed(() => mobile.view.value === "grid")
const scroller = ref<HTMLElement | null>(null)
const { width: viewport } = useElementSize(scroller)
// One column fills the screen next to the rail, with a sliver of the next one showing.
const fullColumnWidth = computed(() =>
	Math.max(MIN_COLUMN, viewport.value - TIME_COLUMN_WIDTH - COLUMN_PEEK),
)
const columnWidth = computed(() => (isGrid.value ? fullColumnWidth.value : null))
const insets = computed(() => ({ top: isGrid.value ? HEADER_HEIGHT : 0, left: TIME_COLUMN_WIDTH }))
const touch = useScheduleTouchDrag(PIXELS_PER_MINUTE, columnWidth, scroller, insets)

const range = board.range
const height = computed(() => (range.value.end - range.value.start) * PIXELS_PER_MINUTE)
const hours = board.hours

const shownRooms = computed(() =>
	isGrid.value ? rooms.value : rooms.value.filter((room) => room.name === mobile.activeRoom.value),
)
// A move follows the finger and shows a placeholder at its landing spot; only a resize reshapes the block.
const resizing = computed(() => (touch.moving.value ? null : touch.position.value))
const displayed = computed(() =>
	dayItems.value.map((item) =>
		resizing.value?.key === item.key ? { ...item, ...resizing.value } : item,
	),
)
const columns = computed(() =>
	shownRooms.value.map((room) => {
		// An all-track item shows in every track, beside whatever it overlaps.
		const items = displayed.value.filter((item) => !item.room || item.room === room.name)
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

const placeholderStyle = (start: number, minutes = PLACEHOLDER_MINUTES) => ({
	top: `${top(start)}px`,
	height: `${minutes * PIXELS_PER_MINUTE - 2}px`,
})

const sheet = mobile.sheet
function placeholderFor(room: string) {
	const landingPosition = touch.moving.value
	if (landingPosition)
		return !landingPosition.room || landingPosition.room === room
			? placeholderAt(room, landingPosition.start, landingPosition.duration)
			: null
	return sheet.value?.type === "add" && sheet.value.room === room
		? placeholderAt(room, sheet.value.start, PLACEHOLDER_MINUTES)
		: null
}
const placeholderAt = (room: string, start: number, duration: number) => ({
	room,
	start,
	duration,
	axis: "y" as const,
	span: false,
})
const gridLines = computed(() => {
	const hour = 60 * PIXELS_PER_MINUTE
	return `repeating-linear-gradient(to bottom, var(--outline-gray-1) 0 1px, transparent 1px ${hour}px)`
})
const empty = computed(() => !dayItems.value.length && !sheet.value)
</script>

<template>
	<div class="relative min-h-0 flex-1">
		<div
			ref="scroller"
			class="h-full scroll-pl-[48px] overflow-auto overscroll-contain"
			:class="isGrid && !touch.position.value && 'snap-x snap-mandatory'"
		>
			<div
				:style="{
					minWidth: `${TIME_COLUMN_WIDTH + (isGrid ? fullColumnWidth * (columns.length + 1) : 0)}px`,
				}"
			>
				<div
					v-if="isGrid"
					class="sticky top-0 z-[6] flex border-b border-outline-gray-1 bg-surface-base"
				>
					<div
						class="sticky left-0 z-[1] shrink-0 bg-surface-base"
						:style="{ width: `${TIME_COLUMN_WIDTH}px` }"
					/>
					<div
						v-for="column in columns"
						:key="column.room.name"
						class="box-border flex min-w-0 shrink-0 snap-start gap-1.5 border-l border-outline-gray-1 p-2.5 text-p-xs font-semibold text-ink-gray-8"
						:style="{ width: `${fullColumnWidth}px` }"
					>
						<span class="truncate">{{ column.room.title }}</span>
						<span class="shrink-0 font-normal text-ink-gray-5">{{
							column.items.length || ""
						}}</span>
					</div>
					<button
						type="button"
						class="box-border flex shrink-0 snap-start items-center gap-1.5 border-l border-outline-gray-1 p-2.5 text-p-xs font-medium text-ink-gray-6 active:bg-surface-gray-2"
						:style="{ width: `${fullColumnWidth}px` }"
						@click="mobile.addRoom"
					>
						<span class="lucide-plus size-3.5" aria-hidden="true" />Add track
					</button>
				</div>
				<div class="relative flex pb-40" :style="{ paddingTop: `${GRID_PADDING}px` }">
					<div
						class="sticky left-0 z-[4] shrink-0 bg-surface-base"
						:style="{ width: `${TIME_COLUMN_WIDTH}px`, height: `${height}px` }"
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
							width: isGrid ? `${fullColumnWidth}px` : undefined,
							backgroundImage: gridLines,
						}"
						@click="tapSlot($event, column.room.name)"
					>
						<SchedulePlaceholder
							v-if="placeholderFor(column.room.name)"
							class="inset-x-[3px]"
							:placeholder="placeholderFor(column.room.name)!"
							:style="
								placeholderStyle(
									placeholderFor(column.room.name)!.start,
									placeholderFor(column.room.name)!.duration,
								)
							"
						/>
						<ScheduleMobileBlock
							v-for="entry in column.items"
							:key="entry.item.key"
							:item="entry.item"
							:height="lengthOf(entry.item)"
							:conflict="conflicts[entry.item.key]"
							:dragging="touch.position.value?.key === entry.item.key"
							:offset="touch.moving.value?.key === entry.item.key ? touch.offset.value : null"
							:landingPosition-start="
								touch.moving.value?.key === entry.item.key ? touch.moving.value.start : undefined
							"
							:style="blockStyle(entry.item, entry.lane, entry.lanes)"
							@press="(event, mode) => touch.begin(event, entry.item, mode)"
							@open="mobile.openEdit(entry.item.key)"
						/>
					</div>
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
