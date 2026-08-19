<script setup lang="ts">
import TimelineList from "@/components/dashboard/TimelineList.vue";
import EventCard from "@/components/dashboard/events/EventCard.vue";
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue";
import { useMyEvents } from "@/data/events";
import { currentTeam } from "@/data/teams";
import { groupEventsByMonth } from "@/utils/eventGroups";
import type { TimelineTab } from "@/utils/timelineTabs";
import { computed, ref } from "vue";

const myEvents = useMyEvents();

const tab = ref<TimelineTab>("upcoming");

// Reuses the feed the Events page already loads: a member sees every event their own
// team hosts, so filtering that feed by team is the team's whole calendar.
const months = computed(() =>
	groupEventsByMonth(
		(myEvents.data?.[tab.value] || []).filter(
			(event) => event.team === currentTeam.value?.name
		)
	)
);
</script>

<template>
	<TeamPageHeader title="Events" />

	<TimelineList
		v-model:tab="tab"
		heading="Events"
		noun="events"
		:months="months"
		:loading="myEvents.loading"
		:error="myEvents.error"
	>
		<!-- Every event here belongs to the team, so a per-card Manage button says nothing. -->
		<template #default="{ item }">
			<EventCard :event="item" :show-manage="false" />
		</template>
	</TimelineList>
</template>
