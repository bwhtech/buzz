<script setup lang="ts">
import { Icon } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
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
		heading="My Calendar"
		icon="lucide-calendar-days"
		noun="events"
		:months="months"
		:loading="myEvents.loading"
		:error="myEvents.error"
	>
		<template #empty-state>
			<EmptyState
				:title="`No ${tab} events`"
				:description="
					tab === 'upcoming'
						? 'Events you host or hold a ticket to will show up here.'
						: 'Events you have already attended or hosted will show up here.'
				"
			>
				<template #illustration>
					<Icon name="lucide-ghost" class="size-8 text-ink-gray-4" />
				</template>
			</EmptyState>
		</template>

		<template #default="{ item }">
			<EventCard :event="item" />
		</template>
	</TimelineList>
</template>
