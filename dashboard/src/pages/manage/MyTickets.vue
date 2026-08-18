<script setup lang="ts">
import PrintedTicket from "@/components/dashboard/tickets/PrintedTicket.vue";
import { useMyTickets } from "@/data/tickets";
import type { TicketWithEvent } from "@/types";
import { dayLabel, monthLabel, weekday } from "@/utils/dateLabels";
import { groupEventsByMonth } from "@/utils/eventGroups";
import { ErrorMessage, LoadingText, TabButtons, dayjs } from "frappe-ui";
import { computed, ref } from "vue";

const tab = ref<"upcoming" | "past">("upcoming");
const tabOptions = [
	{ label: "Upcoming", value: "upcoming" },
	{ label: "Past", value: "past" },
];

const tickets = useMyTickets();

// A ticket whose event was deleted has no date to file it under, so it drops out.
const dated = computed(() =>
	(tickets.data || []).filter((ticket): ticket is TicketWithEvent =>
		Boolean(ticket.start_date && ticket.event_title)
	)
);

const months = computed(() => {
	const today = dayjs().format("YYYY-MM-DD");
	const upcoming = tab.value === "upcoming";
	// Same rule as the events feed: an event running through today is not over yet.
	const isOver = (ticket: TicketWithEvent) => (ticket.end_date || ticket.start_date) < today;
	const shown = dated.value
		.filter((ticket) => isOver(ticket) !== upcoming)
		.sort((a, b) =>
			upcoming
				? a.start_date.localeCompare(b.start_date)
				: b.start_date.localeCompare(a.start_date)
		);
	return groupEventsByMonth(shown);
});
</script>

<template>
	<div class="m-auto max-w-[800px] w-full py-8 px-4 space-y-6">
		<header class="flex items-center justify-between">
			<h1 class="font-semibold text-4xl">Tickets</h1>
			<TabButtons v-model="tab" :options="tabOptions" size="md" />
		</header>

		<ErrorMessage v-if="tickets.error" :message="tickets.error.message" />

		<LoadingText v-else-if="tickets.loading" text="Loading tickets..." />

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
							<PrintedTicket
								v-for="ticket in day.events"
								:key="ticket.name"
								:ticket="ticket"
							/>
						</div>
					</div>
				</div>
			</section>
		</div>

		<p
			v-if="!months.length && !tickets.loading && !tickets.error"
			class="text-base text-ink-gray-5"
		>
			No {{ tab }} tickets.
		</p>
	</div>
</template>
