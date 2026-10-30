<script setup lang="ts">
import { Button, TabButtons, dayjs } from "frappe-ui"
import { computed } from "vue"

import { useBoard, useBuilder } from "../useScheduleBoard"
import ScheduleMobileChip from "./ScheduleMobileChip.vue"
import { ALL_TRACKS, type MobileView, useMobile } from "./useScheduleMobile"

const builder = useBuilder()
const board = useBoard()
const mobile = useMobile()

const VIEW_OPTIONS = [
	{ label: "List", value: "list", iconLeft: "lucide-list" },
	{ label: "Track", value: "track", iconLeft: "lucide-rectangle-vertical" },
	{ label: "Grid", value: "grid", iconLeft: "lucide-columns-3" },
]

const items = computed(() => builder.dayItems(builder.activeDate.value))
const unscheduled = mobile.unscheduledTalks
const isTrackView = computed(() => mobile.view.value === "track")
const showTracks = computed(() => mobile.view.value !== "grid")
const countIn = (track: string) => items.value.filter((item) => item.track === track).length
const tracks = computed(() =>
	builder.tracks.tracks.value.map((track) => ({
		name: track.name,
		title: track.title,
		count: countIn(track.name),
	})),
)
const isTrackActive = (name: string) =>
	isTrackView.value ? mobile.activeTrack.value === name : mobile.trackFilter.value === name

function pickDay(date: string) {
	builder.activeDate.value = date
	board.select(null)
}

function pickTrack(name: string) {
	if (isTrackView.value) mobile.chosenTrack.value = name
	else mobile.trackFilter.value = name
}
</script>

<template>
	<div class="flex shrink-0 flex-col gap-3 border-b border-outline-gray-1 pb-3 pt-1">
		<div v-if="unscheduled.length" class="flex justify-end px-4">
			<Button
				variant="subtle"
				size="sm"
				iconLeft="lucide-inbox"
				:label="`${unscheduled.length} to place`"
				@click="mobile.openAdd()"
			/>
		</div>
		<div
			class="[scrollbar-width:none] [&::-webkit-scrollbar]:hidden flex gap-2 overflow-x-auto px-4"
			aria-label="Days"
		>
			<ScheduleMobileChip
				v-for="day in builder.days.value"
				:key="day.date"
				size="lg"
				:active="builder.activeDate.value === day.date"
				@click="pickDay(day.date)"
			>
				{{ day.label }}
				<template #count>{{ dayjs(day.date).format("ddd D") }}</template>
			</ScheduleMobileChip>
		</div>
		<div class="px-4">
			<TabButtons
				fluid
				:model-value="mobile.view.value"
				:options="VIEW_OPTIONS"
				@update:model-value="(value) => (mobile.view.value = value as MobileView)"
			/>
		</div>
		<div
			v-if="showTracks"
			class="[scrollbar-width:none] [&::-webkit-scrollbar]:hidden flex gap-1.5 overflow-x-auto px-4"
		>
			<ScheduleMobileChip
				v-if="!isTrackView"
				:active="mobile.trackFilter.value === ALL_TRACKS"
				@click="pickTrack(ALL_TRACKS)"
			>
				All
				<template #count>{{ items.length }}</template>
			</ScheduleMobileChip>
			<ScheduleMobileChip
				v-for="track in tracks"
				:key="track.name"
				:active="isTrackActive(track.name)"
				@click="pickTrack(track.name)"
			>
				{{ track.title }}
				<template #count>{{ track.count }}</template>
			</ScheduleMobileChip>
			<button
				type="button"
				class="flex h-[30px] shrink-0 items-center gap-1 rounded-full border border-dashed border-outline-gray-3 px-3 text-p-sm text-ink-gray-6"
				@click="mobile.addTrack"
			>
				<span class="lucide-plus size-3.5" aria-hidden="true" />Track
			</button>
		</div>
	</div>
</template>
