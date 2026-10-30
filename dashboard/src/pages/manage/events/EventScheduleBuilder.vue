<script setup lang="ts">
import { useEventListener } from "@vueuse/core"
import { useRouteQuery } from "@vueuse/router"
import { Button, ErrorMessage, Spinner, TabButtons } from "frappe-ui"
import { computed, onMounted } from "vue"
import { onBeforeRouteLeave, useRoute } from "vue-router"

import ScheduleMobile from "@/components/dashboard/schedule/mobile/ScheduleMobile.vue"
import ScheduleCalendar from "@/components/dashboard/schedule/ScheduleCalendar.vue"
import ScheduleDayNav from "@/components/dashboard/schedule/ScheduleDayNav.vue"
import ScheduleHeader from "@/components/dashboard/schedule/ScheduleHeader.vue"
import ScheduleQuickAdd from "@/components/dashboard/schedule/ScheduleQuickAdd.vue"
import ScheduleRail from "@/components/dashboard/schedule/ScheduleRail.vue"
import ScheduleTimeline from "@/components/dashboard/schedule/ScheduleTimeline.vue"
import ScheduleToast from "@/components/dashboard/schedule/ScheduleToast.vue"
import type { ScheduleView } from "@/components/dashboard/schedule/scheduleTypes"
import { provideSchedule, useScheduleBoard } from "@/components/dashboard/schedule/useScheduleBoard"
import { useScheduleBuilder } from "@/components/dashboard/schedule/useScheduleBuilder"
import { useIsMobile } from "@/composables/useIsMobile"
import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"

const route = useRoute()
const isMobile = useIsMobile()
const eventId = route.params.eventId as string
const event = useEventDoc(() => eventId)
const builder = useScheduleBuilder(() => eventId)

const VIEWS: ScheduleView[] = ["calendar", "timeline"]
const view = useRouteQuery<ScheduleView>("view", "calendar", {
	transform: (value) =>
		VIEWS.includes(value as ScheduleView) ? (value as ScheduleView) : "calendar",
})
const board = useScheduleBoard(builder, view)
provideSchedule(builder, board)
onMounted(() => builder.open())

const VIEW_OPTIONS = [
	{ label: "Calendar", value: "calendar", iconLeft: "lucide-columns-3" },
	{ label: "Timeline", value: "timeline", iconLeft: "lucide-chart-gantt" },
]
const VIEW_COMPONENTS = {
	calendar: ScheduleCalendar,
	timeline: ScheduleTimeline,
}

const loadError = computed(
	() => (builder.schedule.error ?? builder.openCall.error) as FrappeError | null,
)
const hasRooms = computed(() => builder.rooms.rooms.value.length > 0)
const dayIsEmpty = computed(
	() =>
		hasRooms.value &&
		!builder.dayItems(builder.activeDate.value).length &&
		!board.dragging.value &&
		!board.quickAdd.value,
)

function openCustom() {
	board.tab.value = "custom"
	board.select(null)
}

const UNSAVED = "Leave without saving? Your changes to this schedule will be lost."
onBeforeRouteLeave(
	() => !(builder.isPublished.value && builder.dirty.value) || window.confirm(UNSAVED),
)
useEventListener(window, "beforeunload", (e) => builder.dirty.value && e.preventDefault())
</script>

<template>
	<ScheduleMobile v-if="isMobile" :event-id="eventId" />
	<div v-else class="flex h-full min-h-0 flex-col bg-surface-base">
		<ScheduleHeader :event-id="eventId" />
		<div v-if="loadError" class="p-8"><ErrorMessage :message="loadError.message" /></div>
		<div v-else-if="!builder.draft.value" class="grid flex-1 place-items-center">
			<Spinner class="size-5" />
		</div>
		<template v-else>
			<div
				class="flex shrink-0 flex-wrap items-center gap-3 border-b border-outline-gray-1 py-1.5 pb-2.5 pl-5 pr-4"
			>
				<ScheduleDayNav />
				<div class="flex-1" />
				<TabButtons v-model="view" :options="VIEW_OPTIONS" />
				<Button variant="subtle" iconLeft="lucide-plus" label="Add item" @click="openCustom" />
			</div>
			<div class="relative flex min-h-0 flex-1">
				<div class="relative flex min-w-0 flex-1 flex-col">
					<component :is="VIEW_COMPONENTS[view]" :time-zone="event.doc?.time_zone_label" />
					<div
						v-if="dayIsEmpty"
						class="pointer-events-none absolute left-1/2 top-24 z-[9] flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full border border-outline-gray-2 bg-surface-base px-3.5 py-2 text-p-sm text-ink-gray-7 shadow-md"
					>
						<span class="lucide-mouse-pointer-click size-3.5 text-ink-gray-5" aria-hidden="true" />
						{{ builder.activeDay.value?.label }} is empty. Drag a talk in, or click any slot to add
						one.
					</div>
				</div>
				<ScheduleRail />
			</div>
		</template>
		<ScheduleQuickAdd />
		<ScheduleToast />
	</div>
</template>
