<script setup lang="ts">
import { Alert, dayjs } from "frappe-ui"
import { computed, watch } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import CreateEventHeader from "@/components/dashboard/CreateEventHeader.vue"
import EventCard from "@/components/dashboard/events/EventCard.vue"
import EventDrawer from "@/components/dashboard/events/EventDrawer.vue"
import FloatingCreateEventButton from "@/components/dashboard/FloatingCreateEventButton.vue"
import AddEventMenu from "@/components/dashboard/teams/AddEventMenu.vue"
import PendingSubmissions from "@/components/dashboard/teams/PendingSubmissions.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useDrawerSelection } from "@/composables/useDrawerSelection"
import { useIsMobile } from "@/composables/useIsMobile"
import { useRevealOnScroll } from "@/composables/useRevealOnScroll"
import { finishOpening } from "@/composables/useWorkspaceOpening"
import { useMyEvents, useTeamEvents } from "@/data/events"
import { teams } from "@/data/teams"
import type { MyEvent } from "@/types"
import { groupEventsByMonth } from "@/utils/eventGroups"
import { canEditPublicPage } from "@/utils/teamRoles"
import { useTimelineTabQuery } from "@/utils/timelineTabs"

// In the URL, so one link carries the whole view.
const tab = useTimelineTabQuery()

const route = useRoute()
const isMobile = useIsMobile()

const team = computed(() => route.params.teamId as string | undefined)
// A team's calendar also lists the events its community approved, which the personal feed leaves out.
const myEvents = team.value ? useTeamEvents(() => team.value as string) : useMyEvents()
const canReview = computed(() =>
	canEditPublicPage(teams.value.find((option) => option.name === team.value)?.team_role),
)

// The team workspace opens on this page, so its first load ends the opening screen.
watch(
	() => !myEvents.loading && Boolean(myEvents.data || myEvents.error),
	(loaded) => loaded && finishOpening(),
	{ immediate: true },
)

// The feed arrives already split, so the tab only picks a side.
const events = computed(() => myEvents.data?.[tab.value] || [])

// The feed is unpaginated, so a long history renders a page at a time as it scrolls.
const { visible, sentinel, reset } = useRevealOnScroll(() => events.value, 50)
watch(tab, reset)

// An event already under way is still on, so it sits under today, not its start date.
const today = dayjs().format("YYYY-MM-DD")
const fileUnder = (event: MyEvent) =>
	tab.value === "upcoming" && event.start_date < today ? today : event.start_date

const months = computed(() => groupEventsByMonth(visible.value, fileUnder))

const drawer = useDrawerSelection<MyEvent>()

const emptyDescription = computed(() =>
	team.value
		? "Events your community hosts or features will show up here."
		: tab.value === "upcoming"
			? "Events you host or hold a ticket to will show up here."
			: "Events you have already attended or hosted will show up here.",
)
</script>

<template>
	<TeamPageHeader v-if="team" section="Calendar" />
	<CreateEventHeader v-else title="Events" />
	<template v-if="team && isMobile">
		<AddEventMenu v-if="canReview" :community="team" can-review @added="myEvents.reload()">
			<FloatingCreateEventButton menu-trigger />
		</AddEventMenu>
		<FloatingCreateEventButton v-else />
	</template>

	<TimelineList
		v-model:tab="tab"
		:heading="team ? undefined : 'Events'"
		icon="lucide-calendar-days"
		noun="events"
		:months="months"
		:loading="myEvents.loading"
		:error="myEvents.error"
	>
		<template v-if="team" #intro>
			<Alert
				class="[&_[data-slot=prefix]]:size-7"
				:description="
					__(
						'Your calendar brings together every event your community hosts and every event it features. When you approve an event submitted by another organizer, it shows up here and on your community page.',
					)
				"
			>
				<template #prefix>
					<span
						class="flex size-7 items-center justify-center rounded-5 bg-surface-gray-3 text-ink-gray-9"
						aria-hidden="true"
					>
						<svg viewBox="0 0 16 16" class="size-4" fill="currentColor">
							<rect x="4" y="1" width="1.5" height="3" rx="0.75" />
							<rect x="10.5" y="1" width="1.5" height="3" rx="0.75" />
							<path
								d="M1.5 5.5a2.5 2.5 0 0 1 2.5-2.5h8a2.5 2.5 0 0 1 2.5 2.5v7a2.5 2.5 0 0 1-2.5 2.5H4a2.5 2.5 0 0 1-2.5-2.5zm3 2.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5m3.5 0a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5m3.5 0a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5M4.5 11.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5m3.5 0a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5"
								fill-rule="evenodd"
							/>
						</svg>
					</span>
				</template>
				<template #title>
					<span class="text-lg font-semibold text-ink-gray-9">
						{{ __("Welcome to your community calendar") }}
					</span>
				</template>
			</Alert>
			<PendingSubmissions :community="team" :can-review="canReview" @changed="myEvents.reload()" />
		</template>
		<template v-if="team" #heading>
			<h2 class="hidden text-2xl font-semibold text-ink-gray-9 md:block">{{ __("Events") }}</h2>
		</template>
		<template v-if="team && canReview && !isMobile" #actions>
			<AddEventMenu :community="team" can-review @added="myEvents.reload()" />
		</template>
		<template #empty-state>
			<EmptyState :title="`No ${tab} events`" :description="emptyDescription" icon="lucide-ghost" />
		</template>

		<template #default="{ item }">
			<EventCard :event="item" @open="drawer.show(item)" />
		</template>

		<template #footer>
			<div ref="sentinel" aria-hidden="true" />
		</template>
	</TimelineList>

	<EventDrawer v-model:open="drawer.open.value" :event="drawer.selected.value" />
</template>
