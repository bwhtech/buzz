<script setup lang="ts">
import EventGuestItem from "@/components/dashboard/events/EventGuestItem.vue";
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue";
import { eventDetail, eventGuests } from "@/data/events";
import { FormControl, LoadingText } from "frappe-ui";
import { computed, ref } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const eventId = route.params.eventId as string;

const event = eventDetail(eventId);
const guests = eventGuests(eventId);

const query = ref("");

// Filtered here rather than server-side: the whole list is already loaded, so a round
// trip per keystroke would be slower than the search it replaces.
const matches = computed(() => {
	const term = query.value.trim().toLowerCase();
	const all = guests.data?.guests ?? [];
	if (!term) return all;
	return all.filter((guest) =>
		[guest.attendee_name, guest.attendee_email].some((field) =>
			field?.toLowerCase().includes(term)
		)
	);
});
</script>

<template>
	<EventPageHeader :title="event.data?.title" section="Guests" />

	<div class="m-auto max-w-[800px] w-full py-8 px-4 space-y-8">
		<section class="space-y-2">
			<h1 class="text-xl font-semibold text-ink-gray-9">How it's going</h1>

			<p class="flex items-baseline gap-1.5">
				<span class="text-2xl font-semibold tabular-nums text-ink-gray-9">
					{{ guests.data?.total ?? "—" }}
				</span>
				<span class="text-base text-ink-gray-5">registered</span>
			</p>

			<p v-if="guests.data?.registrations_closed" class="text-sm text-ink-red-3">
				Registrations have closed
			</p>
			<p v-else-if="guests.data" class="text-sm text-ink-gray-5">Registrations are open</p>
		</section>

		<section class="space-y-3">
			<h2 class="text-xl font-semibold text-ink-gray-9">Guest list</h2>

			<FormControl
				v-model="query"
				type="text"
				placeholder="Search by name or email"
				aria-label="Search guests"
			>
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
			</FormControl>

			<LoadingText v-if="guests.loading" text="Loading guests…" />

			<ul
				v-else-if="matches.length"
				class="divide-y divide-outline-gray-1 overflow-hidden rounded-xl border border-outline-gray-2"
			>
				<EventGuestItem v-for="guest in matches" :key="guest.name" :guest="guest" />
			</ul>

			<p v-else-if="query" class="text-base text-ink-gray-5">
				Nobody here matches “{{ query }}”.
			</p>
			<p v-else class="text-base text-ink-gray-5">No guests yet.</p>
		</section>
	</div>
</template>
