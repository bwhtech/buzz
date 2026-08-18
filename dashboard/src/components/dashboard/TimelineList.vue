<script setup lang="ts" generic="T extends { name: string }">
import { dayLabel, monthLabel, weekday } from "@/utils/dateLabels";
import type { MonthGroup } from "@/utils/eventGroups";
import type { TimelineTab } from "@/utils/timelineTabs";
import { ErrorMessage, LoadingText, TabButtons } from "frappe-ui";

defineProps<{
	heading: string;
	// Names the rows in "Loading tickets..." and "No upcoming tickets.".
	noun: string;
	months: MonthGroup<T>[];
	loading?: boolean;
	error?: { message: string } | null;
}>();

const tab = defineModel<TimelineTab>("tab", { required: true });

const tabOptions = [
	{ label: "Upcoming", value: "upcoming" },
	{ label: "Past", value: "past" },
];
</script>

<template>
	<div class="m-auto max-w-[800px] w-full py-8 px-4 space-y-6">
		<header class="flex items-center justify-between">
			<h1 class="font-semibold text-4xl">{{ heading }}</h1>
			<TabButtons v-model="tab" :options="tabOptions" size="md" />
		</header>

		<ErrorMessage v-if="error" :message="error.message" />

		<LoadingText v-else-if="loading" :text="`Loading ${noun}...`" />

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
							<template v-for="item in day.events" :key="item.name">
								<slot :item="item" />
							</template>
						</div>
					</div>
				</div>
			</section>
		</div>

		<p v-if="!months.length && !loading && !error" class="text-base text-ink-gray-5">
			No {{ tab }} {{ noun }}.
		</p>
	</div>
</template>
