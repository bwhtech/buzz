<script setup lang="ts">
import TimelineList from "@/components/dashboard/TimelineList.vue";
import EventCard from "@/components/dashboard/events/EventCard.vue";
import type { MyEvents } from "@/types";
import { groupEventsByMonth } from "@/utils/eventGroups";
import type { TimelineTab } from "@/utils/timelineTabs";
import { useCall } from "frappe-ui";
import { computed, ref } from "vue";

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this user's feed to IndexedDB past a logout.
const myEvents = useCall<MyEvents>({
	url: "/api/v2/method/buzz.api.events.get_my_events",
});

const tab = ref<TimelineTab>("upcoming");

// The feed arrives already split, so the tab only picks a side.
const months = computed(() => groupEventsByMonth(myEvents.data?.[tab.value] || []));
</script>

<template>
	<TimelineList
		v-model:tab="tab"
		heading="Events"
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
