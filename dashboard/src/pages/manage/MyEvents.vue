<script setup lang="ts">
import { Icon } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import EventCard from "@/components/dashboard/events/EventCard.vue"
import EventDrawer from "@/components/dashboard/events/EventDrawer.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useMyEvents } from "@/data/events"
import type { MyEvent } from "@/types"
import { groupEventsByMonth } from "@/utils/eventGroups"
import type { TimelineTab } from "@/utils/timelineTabs"

const myEvents = useMyEvents()

const tab = ref<TimelineTab>("upcoming")

// The feed arrives already split, so the tab only picks a side.
const months = computed(() => groupEventsByMonth(myEvents.data?.[tab.value] || []))

// Held past the close so the drawer keeps its contents while it animates out.
const selected = ref<MyEvent | null>(null)
const drawerOpen = ref(false)

function openEvent(event: MyEvent) {
	selected.value = event
	drawerOpen.value = true
}
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

		<!-- The overlay button covers the card rather than wrapping it: EventCard's Manage
		     link is interactive content, which cannot legally nest inside a button. Manage
		     is raised above the overlay, so both targets work and both are focusable. -->
		<template #default="{ item }">
			<div class="event-row relative rounded-8">
				<button
					type="button"
					class="absolute inset-0 rounded-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-3"
					:aria-label="`Open ${item.title}`"
					@click="openEvent(item)"
				/>
				<EventCard :event="item" />
			</div>
		</template>
	</TimelineList>

	<EventDrawer v-model:open="drawerOpen" :event="selected" />
</template>

<style scoped>
/* A row that is a button has to answer the press. The scale stays near-imperceptible
   because these are seen dozens of times a session. */
.event-row {
	transition: transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}
.event-row:active {
	transform: scale(0.995);
}

@media (prefers-reduced-motion: reduce) {
	.event-row {
		transition: none;
	}
	.event-row:active {
		transform: none;
	}
}
</style>
