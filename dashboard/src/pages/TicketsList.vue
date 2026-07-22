<template>
	<div>
		<div v-if="tickets.loading" class="flex justify-center py-8">
			<div class="text-ink-gray-6">{{ __("Loading tickets...") }}</div>
		</div>

		<div
			v-else-if="tickets.error"
			class="bg-surface-red-1 border border-outline-red-1 rounded-lg p-4"
		>
			<p class="text-ink-red-6">
				{{ __("Error loading tickets") }}: {{ tickets.error.message }}
			</p>
		</div>

		<ListView
			v-else
			:columns="columns"
			:rows="tickets.data || []"
			row-key="name"
			:options="{
				selectable: false,
				getRowRoute: (row: Record<string, any>) => ({
					name: 'ticket-details',
					params: { ticketId: row.name },
				}),
				emptyState: {
					title: __('No tickets found'),
					description: __('You haven\'t purchased any tickets yet.'),
				},
			}"
		>
			<template #cell="{ item }">
				<span>{{ item }}</span>
			</template>
		</ListView>
	</div>
</template>

<script setup lang="ts">
import { ListView, useList } from "frappe-ui";
import { dayjsLocal } from "frappe-ui";
import { session } from "../data/session";

const columns = [
	{ label: __("Attendee Name"), key: "attendee_name" },
	{ label: __("Event"), key: "event_title" },
	{ label: __("Ticket Type"), key: "ticket_type_display" },
	{ label: __("Start Date"), key: "start_date" },
];

const tickets = useList({
	doctype: "Event Ticket",
	fields: [
		"name",
		"attendee_name",
		"attendee_email",
		"ticket_type",
		"ticket_type.title as ticket_type_title",
		"event",
		"event.title as event_title",
		"event.start_date",
		"creation",
	],
	filters: {
		attendee_email: session.user,
		docstatus: ["!=", 0],
	},
	orderBy: "creation desc",
	cacheKey: "tickets-list",
	onError: console.error,
	transform(data: any[]) {
		return data.map((ticket: Record<string, any>) => ({
			...ticket,
			start_date: dayjsLocal(ticket.start_date).format("MMM DD, YYYY"),
			ticket_type_display: ticket.ticket_type_title || ticket.ticket_type,
		}));
	},
});
</script>
