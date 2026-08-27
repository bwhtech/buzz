<script setup lang="ts">
import { computed, ref } from "vue"

import EventCard from "@/components/dashboard/events/EventCard.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useMyEvents } from "@/data/events"
import { groupEventsByMonth } from "@/utils/eventGroups"
import type { TimelineTab } from "@/utils/timelineTabs"

const myEvents = useMyEvents()

const tab = ref<TimelineTab>("upcoming")

// The feed arrives already split, so the tab only picks a side.
const months = computed(() => groupEventsByMonth(myEvents.data?.[tab.value] || []))
</script>

<template>
	<TimelineList
		v-model:tab="tab"
		heading="My Events"
		noun="events"
		:months="months"
		:loading="myEvents.loading"
		:error="myEvents.error"
	>
		<template #default="{ item }">
			<EventCard :event="item" />
		</template>
	</TimelineList>
</template>
