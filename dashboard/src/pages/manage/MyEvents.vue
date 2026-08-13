<script setup lang="ts">
import EventCard from "@/components/dashboard/events/EventCard.vue";
import type { MyEvents } from "@/types";
import { dayLabel, monthLabel, weekday } from "@/utils/dateLabels";
import { groupEventsByMonth } from "@/utils/eventGroups";
import { ErrorMessage, LoadingText, TabButtons, useCall } from "frappe-ui";
import { computed, ref } from "vue";

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this user's feed to IndexedDB past a logout.
const myEvents = useCall<MyEvents>({
	url: "/api/v2/method/buzz.api.events.get_my_events",
});

const tab = ref<"upcoming" | "past">("upcoming");
const tabOptions = [
	{ label: "Upcoming", value: "upcoming" },
	{ label: "Past", value: "past" },
];

const months = computed(() => groupEventsByMonth(myEvents.data?.[tab.value] || []));
</script>

<template>
	<div class="m-auto max-w-[800px] w-full py-8 px-4 space-y-6">
		<header class="flex items-center justify-between">
			<h1 class="font-semibold text-4xl">Events</h1>
			<TabButtons v-model="tab" :options="tabOptions" size="md" />
		</header>

		<ErrorMessage v-if="myEvents.error" :message="myEvents.error.message" />

		<LoadingText v-else-if="myEvents.loading" text="Loading events..." />

		<div v-else class="relative space-y-6">
			<section v-for="month in months" :key="month.month" class="space-y-4">
				<h2
					class="relative bg-surface-elevation-1 py-1 text-xl font-semibold text-ink-gray-8"
				>
					{{ monthLabel(month.month) }}
				</h2>

				<div
					v-for="day in month.days"
					:key="day.date"
					class="grid grid-cols-[6rem_1fr] gap-4"
				>
					<div class="pt-1">
						<p class="font-semibold text-ink-gray-8">{{ dayLabel(day.date) }}</p>
						<p class="text-base text-ink-gray-5">{{ weekday(day.date) }}</p>
					</div>

					<div class="relative space-y-1 pl-6 pb-7">
						<div class="absolute -left-4 flex flex-col items-center h-full">
							<span
								class="size-2 rounded-full bg-surface-gray-4"
								aria-hidden="true"
							/>
							<div
								class="w-px h-full bg-gradient-to-b from-outline-gray-2 from-75% to-transparent"
							></div>
						</div>

						<div class="space-y-6">
							<EventCard
								v-for="event in day.events"
								:key="event.name"
								:event="event"
							/>
						</div>
					</div>
				</div>
			</section>
		</div>

		<p
			v-if="!months.length && !myEvents.loading && !myEvents.error"
			class="text-base text-ink-gray-5"
		>
			No {{ tab }} events.
		</p>
	</div>
</template>
