<script setup lang="ts">
import ProposalCard from "@/components/dashboard/proposals/ProposalCard.vue";
import { myProposals } from "@/data/proposals";
import type { FrappeError, ProposalWithEvent } from "@/types";
import { dayLabel, monthLabel, weekday } from "@/utils/dateLabels";
import { groupEventsByMonth } from "@/utils/eventGroups";
import { type TimelineTab, inTab } from "@/utils/timelineTabs";
import { LoadingText, TabButtons, dayjsLocal } from "frappe-ui";
import { computed, ref } from "vue";

const tab = ref<TimelineTab>("upcoming");
const tabOptions = [
	{
		label: "Upcoming",
		value: "upcoming",
	},
	{
		label: "Past",
		value: "past",
	},
];

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() => (myProposals.error as FrappeError | null)?.message);

// A proposal whose event was deleted has no date to file it under, so it drops out.
const dated = computed(() =>
	(myProposals.data || []).filter((proposal): proposal is ProposalWithEvent =>
		Boolean(proposal.start_date && proposal.event_title)
	)
);

const months = computed(() =>
	groupEventsByMonth(inTab(dated.value, tab.value, dayjsLocal().format("YYYY-MM-DD")))
);
</script>

<template>
	<div class="m-auto max-w-[800px] w-full py-8 px-4 space-y-6">
		<header class="flex items-center justify-between">
			<h1 class="font-semibold text-4xl">Talk Proposals</h1>
			<TabButtons v-model="tab" :options="tabOptions" size="md" />
		</header>

		<LoadingText v-if="myProposals.loading" text="Loading proposals…" />

		<ErrorMessage v-else-if="errorMessage" :message="errorMessage" />

		<div v-else class="space-y-6">
			<section v-for="month in months" :key="month.month" class="space-y-4">
				<h2 class="bg-surface-elevation-1 py-1 text-xl font-semibold text-ink-gray-8">
					{{ monthLabel(month.month) }}
				</h2>

				<div
					v-for="day in month.days"
					:key="day.date"
					class="grid grid-cols-[6rem_1fr] gap-4 pb-4"
				>
					<div class="pt-1">
						<p class="font-semibold text-ink-gray-8">{{ dayLabel(day.date) }}</p>
						<p class="text-base text-ink-gray-5">{{ weekday(day.date) }}</p>
					</div>

					<div class="min-w-0 space-y-4">
						<ProposalCard
							v-for="proposal in day.events"
							:key="proposal.name"
							:proposal="proposal"
						/>
					</div>
				</div>
			</section>

			<p v-if="!months.length" class="text-base text-ink-gray-5">No {{ tab }} proposals.</p>
		</div>
	</div>
</template>
