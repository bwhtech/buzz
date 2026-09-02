<script setup lang="ts">
import { Icon } from "frappe-ui"
import { computed } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import CreateEventHeader from "@/components/dashboard/CreateEventHeader.vue"
import EventCard from "@/components/dashboard/events/EventCard.vue"
import EventDrawer from "@/components/dashboard/events/EventDrawer.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useEventDrawer } from "@/composables/useEventDrawer"
import { useMyEvents } from "@/data/events"
import { groupEventsByMonth } from "@/utils/eventGroups"
import { useTimelineTabQuery } from "@/utils/timelineTabs"

// In the URL, so one link carries the whole view.
const tab = useTimelineTabQuery()

const myEvents = useMyEvents()

// The feed arrives already split, so the tab only picks a side.
const months = computed(() => groupEventsByMonth(myEvents.data?.[tab.value] || []))

const drawer = useEventDrawer()

const emptyDescription = computed(() =>
	tab.value === "upcoming"
		? "Events you host or hold a ticket to will show up here."
		: "Events you have already attended or hosted will show up here.",
)
</script>

<template>
	<CreateEventHeader />

	<TimelineList
		v-model:tab="tab"
		heading="Events"
		icon="lucide-calendar-days"
		noun="events"
		:months="months"
		:loading="myEvents.loading"
		:error="myEvents.error"
	>
		<template #empty-state>
			<EmptyState :title="`No ${tab} events`" :description="emptyDescription">
				<template #illustration>
					<Icon name="lucide-ghost" class="size-8 text-ink-gray-4" />
				</template>
			</EmptyState>
		</template>

		<template #default="{ item }">
			<EventCard :event="item" @open="drawer.show(item)" />
		</template>
	</TimelineList>

	<EventDrawer v-model:open="drawer.open.value" :event="drawer.selected.value" />
</template>
