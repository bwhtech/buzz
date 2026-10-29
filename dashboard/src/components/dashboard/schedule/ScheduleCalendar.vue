<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

import ScheduleLanes from "./ScheduleLanes.vue"
import { dayRange, hourLabel } from "./scheduleTime"
import ScheduleTrackHeader from "./ScheduleTrackHeader.vue"
import type { ScheduleItem, ScheduleItemType, ScheduleTrack } from "./scheduleTypes"

const PIXELS_PER_MINUTE = 1.8
const TIME_COLUMN = 56
const TRACK_MIN_WIDTH = 200

const props = defineProps<{
	items: ScheduleItem[]
	tracks: ScheduleTrack[]
	types: Record<string, ScheduleItemType>
	conflicts: Set<string>
	timeZone?: string | null
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
const height = computed(() => (range.value.end - range.value.start) * PIXELS_PER_MINUTE)
const hours = computed(() => {
	const list = []
	for (let minute = range.value.start; minute < range.value.end; minute += 60) list.push(minute)
	return list
})
const columns = computed(() => `repeat(${props.tracks.length}, minmax(${TRACK_MIN_WIDTH}px, 1fr))`)
const forTrack = (name: string) =>
	props.items.filter((item) => !item.all_tracks && item.track === name)
const spanning = computed(() => props.items.filter((item) => item.all_tracks))
</script>

<template>
	<div class="h-full overflow-auto">
		<div class="flex min-w-max flex-col" :style="{ minWidth: '100%' }">
			<div class="sticky top-0 z-20 flex border-b border-outline-gray-1 bg-surface-base">
				<div
					class="flex shrink-0 items-end justify-end px-2 pb-2 text-p-xs text-ink-gray-5"
					:style="{ width: `${TIME_COLUMN}px` }"
				>
					{{ timeZone }}
				</div>
				<div class="grid flex-1" :style="{ gridTemplateColumns: columns }">
					<ScheduleTrackHeader
						v-for="track in tracks"
						:key="track.name"
						class="border-l border-outline-gray-1"
						:track="track"
						:count="forTrack(track.name).length"
						:can-remove="tracks.length > 1"
						@rename="(title) => emit('renameTrack', track.name, title)"
						@remove="emit('removeTrack', track.name)"
					/>
				</div>
				<div class="flex w-44 shrink-0 items-center px-3">
					<Button
						variant="ghost"
						iconLeft="lucide-plus"
						label="Add room"
						@click="emit('addTrack')"
					/>
				</div>
			</div>

			<div class="flex" :style="{ height: `${height}px` }">
				<div class="relative shrink-0" :style="{ width: `${TIME_COLUMN}px` }">
					<span
						v-for="minute in hours"
						:key="minute"
						class="absolute right-2 -translate-y-1/2 text-p-xs text-ink-gray-5 first:translate-y-1"
						:style="{ top: `${(minute - range.start) * PIXELS_PER_MINUTE}px` }"
					>
						{{ hourLabel(minute) }}
					</span>
				</div>
				<div class="relative flex-1">
					<div class="grid size-full" :style="{ gridTemplateColumns: columns }">
						<div v-for="track in tracks" :key="track.name" class="border-l border-outline-gray-1">
							<ScheduleLanes
								:items="forTrack(track.name)"
								:types="types"
								:conflicts="conflicts"
								vertical
								:pixels-per-minute="PIXELS_PER_MINUTE"
								:range-start="range.start"
								@select="(key) => emit('select', key)"
								@create="(minute) => emit('create', track.name, minute)"
								@drop="(minute, payload) => emit('drop', track.name, minute, payload)"
							/>
						</div>
					</div>
					<div class="pointer-events-none absolute inset-0">
						<ScheduleLanes
							class="pointer-events-none [&_button]:pointer-events-auto"
							:items="spanning"
							:types="types"
							:conflicts="conflicts"
							vertical
							:pixels-per-minute="PIXELS_PER_MINUTE"
							:range-start="range.start"
							:style="{ backgroundImage: 'none' }"
							@select="(key) => emit('select', key)"
						/>
					</div>
				</div>
				<div class="w-44 shrink-0" />
			</div>
		</div>
	</div>
</template>
