<script setup lang="ts">
import { Icon } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import { FilterBar } from "@/components/common/filters"
import type { FilterGroup, FilterOption } from "@/components/common/filters"
import EventCard from "@/components/dashboard/events/EventCard.vue"
import EventDrawer from "@/components/dashboard/events/EventDrawer.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useUrlFilters } from "@/composables/useUrlFilters"
import { useMyEvents } from "@/data/events"
import { teams } from "@/data/teams"
import type { MyEvent } from "@/types"
import { groupEventsByMonth } from "@/utils/eventGroups"
import { useTimelineTabQuery } from "@/utils/timelineTabs"

// In the URL alongside the filters, so one link carries the whole view.
const tab = useTimelineTabQuery()

const filterValues = useUrlFilters(["role", "team", "medium"])

// Declared before the fetch: useCall reads its params getter immediately, so anything the
// getter touches has to exist by then.
// The API takes one value per filter, so only the first selection travels.
const apiFilters = () => {
	const { role = [], team = [], medium = [] } = filterValues.value
	return Object.fromEntries(
		Object.entries({ role: role[0], team: team[0], medium: medium[0] }).filter(
			([, value]) => value,
		),
	) as Record<string, string>
}

const myEvents = useMyEvents(apiFilters)

// Guest and host rather than attending and hosting: the same list is read on the Past tab,
// where an activity reads as a claim about an event that is over. Guest is also what the
// API calls a ticket holder. The empty value is the unfiltered case, which keeps the
// default view on a clean URL.
const ROLE_OPTIONS: FilterOption[] = [
	{ value: "", label: "All Events" },
	{ value: "attending", label: "As a Guest" },
	{ value: "hosting", label: "As a Host" },
]

// The Select's own values, so no mapping table.
const FORMAT_OPTIONS: FilterOption[] = [
	{ value: "In Person", label: "In person" },
	{ value: "Online", label: "Online" },
]

// From data/teams, not the feed: the server now returns only what matches, so the feed can
// no longer supply the full option list. This narrows Team to teams you belong to; an event
// you merely hold a ticket to is still reachable through the role filter.
const teamOptions = computed((): FilterOption[] =>
	teams.value.map((team) => ({ value: team.name, label: team.team_name })),
)

const groups = computed((): FilterGroup[] => [
	{ key: "role", label: "Role", quick: true, single: true, options: ROLE_OPTIONS },
	{ key: "team", label: "Team", options: teamOptions.value },
	{ key: "medium", label: "Format", options: FORMAT_OPTIONS },
])

// The feed arrives filtered and already split, so the tab only picks a side.
const months = computed(() => groupEventsByMonth(myEvents.data?.[tab.value] || []))

// Held past the close so the drawer keeps its contents while it animates out.
const selected = ref<MyEvent | null>(null)
const drawerOpen = ref(false)

const anyFilterActive = computed(() =>
	Object.values(filterValues.value).some((values) => values.length),
)

// A filtered-out list is not an empty feed, and the copy has to say which it is.
const emptyDescription = computed(() => {
	if (anyFilterActive.value) return "No events match these filters. Try clearing a few."
	return tab.value === "upcoming"
		? "Events you host or hold a ticket to will show up here."
		: "Events you have already attended or hosted will show up here."
})

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
		<template #controls>
			<FilterBar v-model="filterValues" :groups="groups" />
		</template>

		<template #empty-state>
			<EmptyState
				:title="anyFilterActive ? 'No matching events' : `No ${tab} events`"
				:description="emptyDescription"
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
