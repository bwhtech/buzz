<script setup lang="ts">
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue";
import { eventDetail, eventGuests } from "@/data/events";
import { LoadingText } from "frappe-ui";
import { useRoute } from "vue-router";

const route = useRoute();
const eventId = route.params.eventId as string;

const event = eventDetail(eventId);
const guests = eventGuests(eventId);
</script>

<template>
	<EventPageHeader :title="event.data?.title" section="Guests" />

	<div class="m-auto max-w-[800px] w-full py-8 px-4 space-y-6">
		<h1 class="font-semibold text-4xl">Event guests</h1>

		<LoadingText v-if="guests.loading" text="Loading guests…" />

		<ul v-else-if="guests.data?.length" class="divide-y divide-outline-gray-1">
			<li
				v-for="guest in guests.data"
				:key="guest.name"
				class="py-3 text-base text-ink-gray-8"
			>
				{{ guest.attendee_name }}
			</li>
		</ul>

		<p v-else class="text-base text-ink-gray-5">No guests yet.</p>
	</div>
</template>
