<script setup lang="ts">
import { Button, dayjs, Icon } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import CreateEventHeader from "@/components/dashboard/CreateEventHeader.vue"
import EventCard from "@/components/dashboard/events/EventCard.vue"
import EventDrawer from "@/components/dashboard/events/EventDrawer.vue"
import FloatingCreateEventButton from "@/components/dashboard/FloatingCreateEventButton.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useDrawerSelection } from "@/composables/useDrawerSelection"
import { useIsMobile } from "@/composables/useIsMobile"
import { finishOpening } from "@/composables/useWorkspaceOpening"
import { useMyEvents } from "@/data/events"
import type { MyEvent } from "@/types"
import { groupEventsByMonth } from "@/utils/eventGroups"
import { useTimelineTabQuery } from "@/utils/timelineTabs"

// In the URL, so one link carries the whole view.
const tab = useTimelineTabQuery()

const route = useRoute()
const isMobile = useIsMobile()

const team = computed(() => route.params.teamId as string | undefined)
const myEvents = useMyEvents((): Record<string, string> => (team.value ? { team: team.value } : {}))

// The team workspace opens on this page, so its first load ends the opening screen.
watch(
	() => !myEvents.loading && Boolean(myEvents.data || myEvents.error),
	(loaded) => loaded && finishOpening(),
	{ immediate: true },
)

// The feed arrives already split, so the tab only picks a side.
const events = computed(() => myEvents.data?.[tab.value] || [])

// The feed is unpaginated, so a long history renders a page at a time.
const PAGE_SIZE = 50
const shownCount = ref(PAGE_SIZE)
watch(tab, () => (shownCount.value = PAGE_SIZE))

// An event already under way is still on, so it sits under today, not its start date.
const today = dayjs().format("YYYY-MM-DD")
const fileUnder = (event: MyEvent) =>
	tab.value === "upcoming" && event.start_date < today ? today : event.start_date

const months = computed(() =>
	groupEventsByMonth(events.value.slice(0, shownCount.value), fileUnder),
)

const drawer = useDrawerSelection<MyEvent>()

const emptyDescription = computed(() =>
	team.value
		? "Events this team hosts will show up here."
		: tab.value === "upcoming"
			? "Events you host or hold a ticket to will show up here."
			: "Events you have already attended or hosted will show up here.",
)
</script>

<template>
	<TeamPageHeader v-if="team" section="Events">
		<Button
			v-if="!isMobile"
			variant="solid"
			icon-left="lucide-plus"
			label="Create Event"
			:route="{ name: 'create-event' }"
		/>
	</TeamPageHeader>
	<CreateEventHeader v-else title="Events" />
	<FloatingCreateEventButton v-if="team && isMobile" />

	<TimelineList
		v-model:tab="tab"
		:heading="team ? undefined : 'Events'"
		icon="lucide-calendar-days"
		noun="events"
		:months="months"
		:loading="myEvents.loading"
		:error="myEvents.error"
	>
		<template #empty-state>
			<EmptyState :title="`No ${tab} events`" :description="emptyDescription">
				<template #illustration>
					<Icon name="lucide-ghost" class="size-5 text-ink-gray-5" />
				</template>
			</EmptyState>
		</template>

		<template #default="{ item }">
			<EventCard :event="item" @open="drawer.show(item)" />
		</template>

		<template #footer>
			<Button
				v-if="events.length > shownCount"
				class="w-full"
				label="Show more"
				@click="shownCount += PAGE_SIZE"
			/>
		</template>
	</TimelineList>

	<EventDrawer v-model:open="drawer.open.value" :event="drawer.selected.value" />
</template>
