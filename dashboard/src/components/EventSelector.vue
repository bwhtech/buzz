<template>
	<div class="mb-6 size-full">
		<!-- Header - only show when there are events -->
		<h2
			v-if="(eventsResource.data?.length ?? 0) > 0"
			class="text-lg font-semibold mb-4 text-gray-900 dark:text-white"
		>
			{{ __("Select Event") }}
		</h2>

		<!-- Loading State -->
		<div v-if="eventsResource.loading" class="min-h-[50vh] flex justify-center items-center">
			<div class="flex flex-col items-center gap-2">
				<Spinner class="w-6 h-6" />
				<div class="flex flex-col items-center">
					<p class="text-gray-600 dark:text-gray-400">{{ __("Loading events...") }}</p>
					<p class="text-gray-600 dark:text-gray-400">
						{{ __("Please wait while we load the events...") }}
					</p>
				</div>
			</div>
		</div>

		<!-- Events List View -->
		<ListView
			v-else
			:columns="columns"
			:rows="eventsResource.data || []"
			row-key="name"
			:options="{
				selectable: false,
				showTooltip: true,
				onRowClick: handleEventSelect,
				emptyState: {
					title: __('No Events Available'),
					description: __(
						'There are currently no active events available for check-in. Events may be scheduled for later dates or may need to be published.'
					),
					button: {
						label: __('Refresh Events'),
						variant: 'solid',
						onClick: () => eventsResource.fetch(),
					},
				},
			}"
		/>
	</div>
</template>

<script setup lang="ts">
import type { BuzzEvent } from "@/types";
import { ListView, Spinner, createListResource, dayjsLocal } from "frappe-ui";

defineProps({
	selectedEvent: {
		type: Object,
		default: null,
	},
});

const emit = defineEmits(["select"]);

const columns = [
	{ label: __("Event"), key: "title", width: 1.5 },
	{ label: __("Starts At"), key: "starts_at" },
	{ label: __("Ends At"), key: "ends_at" },
];

const formatTimestamp = (date?: string, time?: string) => {
	let formattedDate = "";
	let formattedTime = "";

	if (date || time) {
		const dateTimeStr = date ? `${date}${time ? "T" + time : "T00:00:00"}` : undefined;

		const parsed = dayjsLocal(dateTimeStr);

		if (parsed.isValid()) {
			formattedDate = parsed.format("MMM DD, YYYY");
			formattedTime = parsed.format("h:mm A");
		}
	}

	if (!formattedDate && !formattedTime) return "No date specified";
	if (formattedDate && !formattedTime) return formattedDate;
	if (!formattedDate && formattedTime) return formattedTime;
	return `${formattedDate} ${formattedTime}`;
};

const eventsResource = createListResource({
	doctype: "Buzz Event",
	fields: ["name", "title", "start_date", "start_time", "end_date", "end_time"],
	order_by: "start_date desc",
	filters: {
		is_published: 1,
		end_date: [">=", dayjsLocal().format("YYYY-MM-DD")],
	},
	auto: true,
	transform(data: BuzzEvent[]) {
		return data.map((event: BuzzEvent) => ({
			...event,
			starts_at: formatTimestamp(event.start_date, event.start_time),
			ends_at: formatTimestamp(event.end_date, event.end_time),
		}));
	},
});

const handleEventSelect = (event: BuzzEvent) => {
	emit("select", event);
};
</script>
