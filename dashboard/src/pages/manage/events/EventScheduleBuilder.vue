<script setup lang="ts">
import { useEventListener } from "@vueuse/core"
import { useRouteQuery } from "@vueuse/router"
import { Button, ErrorMessage, Spinner, TabButtons } from "frappe-ui"
import { computed, onMounted, ref } from "vue"
import { onBeforeRouteLeave, useRoute } from "vue-router"

import ScheduleCalendar from "@/components/dashboard/schedule/ScheduleCalendar.vue"
import ScheduleDayTabs from "@/components/dashboard/schedule/ScheduleDayTabs.vue"
import ScheduleHeader from "@/components/dashboard/schedule/ScheduleHeader.vue"
import ScheduleItemDialog from "@/components/dashboard/schedule/ScheduleItemDialog.vue"
import ScheduleRail from "@/components/dashboard/schedule/ScheduleRail.vue"
import { defaultMinutes, toTime } from "@/components/dashboard/schedule/scheduleTime"
import ScheduleTimeline from "@/components/dashboard/schedule/ScheduleTimeline.vue"
import type {
	ScheduleItemType,
	ScheduleTalk,
	ScheduleView,
} from "@/components/dashboard/schedule/scheduleTypes"
import { useScheduleBuilder } from "@/components/dashboard/schedule/useScheduleBuilder"
import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"

const route = useRoute()
const eventId = route.params.eventId as string
const builder = useScheduleBuilder(() => eventId)
const event = useEventDoc(() => eventId)
onMounted(() => builder.open())

const VIEWS: ScheduleView[] = ["calendar", "timeline"]
const view = useRouteQuery<string>("view", "calendar", {
	transform: (value) => (VIEWS.includes(value as ScheduleView) ? value : "calendar"),
})
const VIEW_OPTIONS = [
	{ label: "Calendar", value: "calendar", iconLeft: "lucide-columns-3" },
	{ label: "Timeline", value: "timeline", iconLeft: "lucide-align-left" },
]

const typesByName = computed(() =>
	Object.fromEntries(builder.itemTypes.value.map((type) => [type.name, type])),
)
const dayItems = computed(() => builder.dayItems(builder.activeDate.value))
const counts = computed(() =>
	Object.fromEntries(
		builder.days.value.map((day) => [day.date, builder.dayItems(day.date).length]),
	),
)
const loadError = computed(
	() => (builder.schedule.error ?? builder.opener.error) as FrappeError | null,
)

const selectedKey = ref<string | null>(null)
const dialogOpen = ref(false)
const selected = computed(
	() => builder.items.value.find((item) => item.key === selectedKey.value) ?? null,
)
function select(key: string) {
	selectedKey.value = key
	dialogOpen.value = true
}

const place = (track: string | null) => ({ track, all_tracks: track ? (0 as const) : (1 as const) })

function addTalk(talk: ScheduleTalk, track: string | null = null, minute?: number) {
	builder.addItem({
		type: "Talk",
		title: talk.title,
		reference_doctype: "Event Talk",
		reference_document: talk.name,
		...(track ? place(track) : { track: builder.tracks.value[0]?.name ?? null }),
		...(minute === undefined ? {} : { start_time: toTime(minute) }),
	})
}

function addType(type: ScheduleItemType, track: string | null = null, minute?: number) {
	const spansAll = type.name === "Break" && !track
	const item = builder.addItem({
		type: type.name,
		title: type.title,
		duration: defaultMinutes(type.name) * 60,
		...(spansAll ? place(null) : { track: track ?? builder.tracks.value[0]?.name ?? null }),
		...(minute === undefined ? {} : { start_time: toTime(minute) }),
	})
	return item
}

function createItem(track: string | null = null, minute?: number) {
	const type = builder.itemTypes.value.find((entry) => entry.name !== "Talk")
	if (!type) return
	select(addType({ ...type, title: "Untitled item" }, track, minute).key)
}

function dropOnTrack(track: string | null, minute: number, payload: string) {
	const { kind, name } = JSON.parse(payload) as { kind: "talk" | "type"; name: string }
	if (kind === "talk") {
		const talk = builder.talks.value.find((entry) => entry.name === name)
		if (talk) addTalk(talk, track, minute)
		return
	}
	const type = typesByName.value[name]
	if (type) addType(type, track, minute)
}

async function createType(title: string) {
	await builder.insertType.submit({
		title,
		color: "gray",
		team: event.doc?.team,
	} as Partial<ScheduleItemType>)
	await builder.refreshTypes()
}

const UNSAVED = "Leave without saving? Your changes to this schedule will be lost."
onBeforeRouteLeave(() => !builder.dirty.value || window.confirm(UNSAVED))
useEventListener(window, "beforeunload", (e) => builder.dirty.value && e.preventDefault())
</script>

<template>
	<div class="flex h-full min-h-0 flex-col bg-surface-base">
		<ScheduleHeader :builder="builder" :event-id="eventId" />
		<div v-if="loadError" class="p-8">
			<ErrorMessage :message="loadError.message" />
		</div>
		<div v-else-if="!builder.draft.value" class="grid flex-1 place-items-center">
			<Spinner class="size-5" />
		</div>
		<template v-else>
			<div class="flex shrink-0 items-center justify-between gap-3 px-4 py-3">
				<ScheduleDayTabs
					v-model="builder.activeDate.value"
					:days="builder.days.value"
					:counts="counts"
					@add="builder.addDay"
					@edit="builder.editDay"
					@duplicate="builder.duplicateDay"
					@remove="builder.removeDay"
				/>
				<div class="flex items-center gap-2">
					<TabButtons v-model="view" :options="VIEW_OPTIONS" />
					<Button variant="subtle" iconLeft="lucide-plus" label="Add item" @click="createItem()" />
				</div>
			</div>
			<div class="flex min-h-0 flex-1 border-t border-outline-gray-1">
				<div class="min-w-0 flex-1">
					<component
						:is="view === 'timeline' ? ScheduleTimeline : ScheduleCalendar"
						:items="dayItems"
						:tracks="builder.tracks.value"
						:types="typesByName"
						:conflicts="builder.conflicts.value"
						:time-zone="event.doc?.time_zone_label"
						@select="select"
						@create="createItem"
						@drop="dropOnTrack"
						@add-track="builder.addTrack(`Room ${builder.tracks.value.length + 1}`)"
						@rename-track="builder.renameTrack"
						@remove-track="builder.removeTrack"
					/>
				</div>
				<ScheduleRail
					:talks="builder.talks.value"
					:types="builder.itemTypes.value"
					:day-label="builder.activeDay.value?.label || 'this day'"
					@add-talk="(talk) => addTalk(talk)"
					@add-type="(type) => addType(type)"
					@create-type="createType"
				/>
			</div>
		</template>
		<ScheduleItemDialog
			v-model="dialogOpen"
			:item="selected"
			:tracks="builder.tracks.value"
			:types="builder.itemTypes.value"
			@save="(patch) => selectedKey && builder.updateItem(selectedKey, patch)"
			@remove="() => selectedKey && builder.removeItem(selectedKey)"
		/>
	</div>
</template>
