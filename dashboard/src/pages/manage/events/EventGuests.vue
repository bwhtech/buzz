<script setup lang="ts">
import EventGuestItem from "@/components/dashboard/events/EventGuestItem.vue";
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

		<!-- A stat, not a card: the number is the thing, the border was packaging. -->
		<section class="w-fit">
			<p class="text-sm text-ink-gray-5">Registrations</p>
			<p class="text-2xl font-semibold tabular-nums text-ink-gray-9">
				{{ guests.data?.total ?? "—" }}
			</p>
		</section>

		<LoadingText v-if="guests.loading" text="Loading guests…" />

		<ul v-else-if="guests.data?.guests.length" class="divide-y divide-outline-gray-1">
			<EventGuestItem v-for="guest in guests.data.guests" :key="guest.name" :guest="guest" />
		</ul>

		<p v-else class="text-base text-ink-gray-5">No guests yet.</p>
	</div>
</template>
