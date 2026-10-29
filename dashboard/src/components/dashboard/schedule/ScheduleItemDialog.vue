<script setup lang="ts">
import { Button, Dialog, FormControl } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { clockLabel, endMinutes, startMinutes, toTime } from "./scheduleTime"
import type { ScheduleItem, ScheduleItemType, ScheduleTrack } from "./scheduleTypes"

const open = defineModel<boolean>({ required: true })
const props = defineProps<{
	item: ScheduleItem | null
	tracks: ScheduleTrack[]
	types: ScheduleItemType[]
}>()
const emit = defineEmits<{ save: [patch: Partial<ScheduleItem>]; remove: [] }>()

const ALL_ROOMS = "__all__"
const DURATIONS = [15, 30, 45, 60, 90, 120, 180]

const title = ref("")
const type = ref("")
const place = ref(ALL_ROOMS)
const start = ref("")
const minutes = ref(30)

watch(open, (isOpen) => {
	if (!isOpen || !props.item) return
	title.value = props.item.title
	type.value = props.item.type
	place.value = props.item.all_tracks ? ALL_ROOMS : (props.item.track ?? ALL_ROOMS)
	start.value = clockLabel(props.item.start_time)
	minutes.value = endMinutes(props.item) - startMinutes(props.item)
})

const durationOptions = computed(() =>
	[...new Set([...DURATIONS, minutes.value])]
		.toSorted((a, b) => a - b)
		.map((value) => ({ label: `${value} min`, value })),
)
const typeOptions = computed(() =>
	props.types.map((entry) => ({ label: entry.title, value: entry.name })),
)
const placeOptions = computed(() => [
	{ label: "All rooms", value: ALL_ROOMS },
	...props.tracks.map((track) => ({ label: track.title, value: track.name })),
])

function submit() {
	if (!start.value) return
	const allRooms = place.value === ALL_ROOMS
	emit("save", {
		title: title.value.trim(),
		type: type.value,
		all_tracks: allRooms ? 1 : 0,
		track: allRooms ? null : place.value,
		start_time: toTime(Number(start.value.slice(0, 2)) * 60 + Number(start.value.slice(3, 5))),
		duration: Number(minutes.value) * 60,
	})
	open.value = false
}

function remove() {
	emit("remove")
	open.value = false
}
</script>

<template>
	<Dialog v-model="open" title="Schedule item">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<FormControl
				v-model="title"
				label="Title"
				placeholder="Sponsor demo, group photo…"
				autocomplete="off"
			/>
			<div class="grid grid-cols-2 gap-3">
				<FormControl v-model="type" type="select" label="Type" :options="typeOptions" />
				<FormControl v-model="place" type="select" label="Room" :options="placeOptions" />
			</div>
			<div class="grid grid-cols-2 gap-3">
				<FormControl v-model="start" type="time" label="Starts" />
				<FormControl v-model="minutes" type="select" label="Duration" :options="durationOptions" />
			</div>
			<div class="flex items-center gap-2">
				<Button type="button" variant="ghost" theme="red" label="Remove" @click="remove" />
				<Button type="submit" variant="solid" label="Done" class="ml-auto" />
			</div>
		</form>
	</Dialog>
</template>
