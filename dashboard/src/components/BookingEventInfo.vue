<template>
	<div class="bg-surface-elevation-1 border border-outline-gray-1 rounded-lg p-6">
		<div class="mb-8 flex items-center justify-between">
			<h3 class="text-lg-semibold text-ink-gray-9">{{ event.title }}</h3>

			<Button
				:link="`/events/${event.route}`"
				icon-left="external-link"
				variant="subtle"
				size="sm"
				>{{ __("Visit Event Page") }}
			</Button>
		</div>

		<div class="space-y-4">
			<!-- Start Date & Time -->
			<div>
				<div class="flex items-center text-ink-gray-6 mb-1">
					<LucideCalendarDays class="w-4 h-4 mr-2 flex-shrink-0" />
					<span class="text-sm-medium">{{ __("Start Date") }}</span>
				</div>
				<p class="text-ink-gray-9 font-medium">
					{{ formatEventDateTime(event.start_date, event.start_time) }}
				</p>
			</div>

			<!-- End Date & Time -->
			<div v-if="event.end_date">
				<div class="flex items-center text-ink-gray-6 mb-1">
					<LucideCalendarDays class="w-4 h-4 mr-2 flex-shrink-0" />
					<span class="text-sm-medium">{{ __("End Date") }}</span>
				</div>
				<p class="text-ink-gray-9 font-medium">
					{{ formatEventDateTime(event.end_date, event.end_time) }}
				</p>
			</div>

			<!-- Venue -->
			<div v-if="venue">
				<div class="flex items-center text-ink-gray-6 mb-1">
					<LucideMapPin class="w-4 h-4 mr-2 flex-shrink-0" />
					<span class="text-sm-medium">{{ __("Venue") }}</span>
				</div>
				<p class="text-ink-gray-9 font-medium">{{ venue.name }}</p>
				<p v-if="venue.address" class="text-sm text-ink-gray-6 mt-1">
					{{ venue.address }}
				</p>
			</div>

			<!-- Event Description -->
			<div v-if="event.short_description" class="pt-2 border-t border-outline-gray-1">
				<p class="text-sm text-ink-gray-6">{{ event.short_description }}</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { dayjsLocal } from "frappe-ui";
import LucideCalendarDays from "~icons/lucide/calendar-days";
import LucideMapPin from "~icons/lucide/map-pin";

defineProps({
	event: {
		type: Object,
		required: true,
		validator: (value: any) => {
			return (
				typeof value.title === "string" &&
				value.start_date &&
				typeof value.route === "string"
			);
		},
	},
	venue: {
		type: Object,
		default: null,
	},
});

// Helper function to format date and time together (matching TicketDetails.vue)
const formatEventDateTime = (date: string, time: string) => {
	if (!date) return "";

	// Create a date object from the date string
	const dateObj = dayjsLocal(date);

	// If time is provided, combine it with the date
	if (time) {
		// Parse the time (format: "HH:mm:ss")
		const [hours, minutes] = time.split(":");
		const dateTimeObj = dateObj.hour(Number.parseInt(hours)).minute(Number.parseInt(minutes));
		return dateTimeObj.format("MMMM DD, YYYY [at] h:mm A");
	}

	// If no time, just show the date
	return dateObj.format("MMMM DD, YYYY");
};
</script>
