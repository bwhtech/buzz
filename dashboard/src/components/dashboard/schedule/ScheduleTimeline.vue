<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

import ScheduleLanes from "./ScheduleLanes.vue"
import { dayRange, hourLabel } from "./scheduleTime"
import ScheduleTrackHeader from "./ScheduleTrackHeader.vue"
import type { ScheduleItem, ScheduleItemType, ScheduleTrack } from "./scheduleTypes"

const PIXELS_PER_MINUTE = 2.4
const TRACK_COLUMN = 220
const ROW_HEIGHT = 92
const AXIS_HEIGHT = 36

const props = defineProps<{
	items: ScheduleItem[]
	tracks: ScheduleTrack[]
	types: Record<string, ScheduleItemType>
	conflicts: Set<string>
}>()
const emit = defineEmits<{
	select: [key: string]
	create: [track: string | null, minute: number]
	drop: [track: string | null, minute: number, payload: string]
	addTrack: []
	renameTrack: [name: string, title: string]
	removeTrack: [name: string]
}>()

const range = computed(() => dayRange(props.items))
const width = computed(() => (range.value.end - range.value.start) * PIXELS_PER_MINUTE)
const hours = computed(() => {
	const list = []
	for (let minute = range.value.start; minute < range.value.end; minute += 60) list.push(minute)
	return list
})
const forTrack = (name: string) =>
	props.items.filter((item) => !item.all_tracks && item.track === name)
const spanning = computed(() => props.items.filter((item) => item.all_tracks))
</script>

<template>
	<div class="h-full overflow-auto">
		<div class="min-w-max" :style="{ width: `${TRACK_COLUMN + width}px` }">
			<div
				class="sticky top-0 z-20 flex border-b border-outline-gray-1 bg-surface-base"
				:style="{ height: `${AXIS_HEIGHT}px` }"
			>
				<div
					class="sticky left-0 z-10 flex shrink-0 items-center bg-surface-base px-3 text-p-xs text-ink-gray-5"
					:style="{ width: `${TRACK_COLUMN}px` }"
				>
					Rooms
				</div>
				<div class="relative" :style="{ width: `${width}px` }">
					<span
						v-for="minute in hours"
						:key="minute"
						class="absolute top-1/2 -translate-y-1/2 pl-2 text-p-xs text-ink-gray-5"
						:style="{ left: `${(minute - range.start) * PIXELS_PER_MINUTE}px` }"
					>
						{{ hourLabel(minute) }}
					</span>
				</div>
			</div>

			<div class="relative">
				<div
					v-for="track in tracks"
					:key="track.name"
					class="flex border-b border-outline-gray-1"
					:style="{ height: `${ROW_HEIGHT}px` }"
				>
					<div
						class="sticky left-0 z-10 shrink-0 bg-surface-base"
						:style="{ width: `${TRACK_COLUMN}px` }"
					>
						<ScheduleTrackHeader
							class="h-full"
							:track="track"
							:count="forTrack(track.name).length"
							:can-remove="tracks.length > 1"
							@rename="(title) => emit('renameTrack', track.name, title)"
							@remove="emit('removeTrack', track.name)"
						/>
					</div>
					<div class="border-l border-outline-gray-1" :style="{ width: `${width}px` }">
						<ScheduleLanes
							:items="forTrack(track.name)"
							:types="types"
							:conflicts="conflicts"
							:vertical="false"
							:pixels-per-minute="PIXELS_PER_MINUTE"
							:range-start="range.start"
							@select="(key) => emit('select', key)"
							@create="(minute) => emit('create', track.name, minute)"
							@drop="(minute, payload) => emit('drop', track.name, minute, payload)"
						/>
					</div>
				</div>
				<div
					class="pointer-events-none absolute inset-y-0"
					:style="{ left: `${TRACK_COLUMN}px`, width: `${width}px` }"
				>
					<ScheduleLanes
						class="pointer-events-none [&_button]:pointer-events-auto"
						:items="spanning"
						:types="types"
						:conflicts="conflicts"
						:vertical="false"
						:pixels-per-minute="PIXELS_PER_MINUTE"
						:range-start="range.start"
						:style="{ backgroundImage: 'none' }"
						@select="(key) => emit('select', key)"
					/>
				</div>
			</div>
			<div class="sticky left-0 px-3 py-3">
				<Button variant="ghost" iconLeft="lucide-plus" label="Add room" @click="emit('addTrack')" />
			</div>
		</div>
	</div>
</template>
