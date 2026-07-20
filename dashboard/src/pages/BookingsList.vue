<template>
	<div>
		<ListView
			v-if="bookings.data"
			:columns="columns"
			:rows="bookings.data"
			row-key="name"
			:options="{
				selectable: false,
				getRowRoute: (row) => ({
					name: 'booking-details',
					params: { bookingId: row.name },
				}),
				emptyState: {
					title: __('No bookings found'),
					description: __('You haven\'t made any bookings yet.'),
				},
			}"
		>
			<template #cell="{ item, row, column, align }">
				<Badge
					v-if="column.key === 'status'"
					:theme="
						row.status === 'Approved' || row.status === 'Confirmed'
							? 'green'
							: row.status === 'Approval Pending'
							? 'yellow'
							: 'red'
					"
					variant="subtle"
					size="sm"
				>
					{{ item }}
				</Badge>
				<ListRowItem v-else :column="column" :row="row" :item="item" :align="align" />
			</template>
		</ListView>
	</div>
</template>

<script setup>
import { formatCurrency } from "@/utils/currency";
import { pluralize } from "@/utils/pluralize";
import { Badge, ListRowItem, ListView, useList } from "frappe-ui";
import { dayjsLocal } from "frappe-ui";
import { session } from "../data/session";

const columns = [
	{ label: __("Event"), key: "event_title", width: "220px" },
	{ label: "", key: "ticket_count", width: "90px" },
	{ label: __("Start Date"), key: "start_date", width: "110px" },
	{ label: __("Venue"), key: "venue", width: "140px" },
	{ label: __("Amount Paid"), key: "formatted_amount", width: "110px" },
	{ label: __("Status"), key: "status", width: "120px" },
];

const bookings = useList({
	doctype: "Event Booking",
	fields: [
		"name",
		"event",
		"event.title as event_title",
		"event.start_date",
		"event.venue",
		"docstatus",
		"total_amount",
		"currency",
		"creation",
		"status",
		{ attendees: ["ticket_type"] },
	],
	filters: { user: session.user, docstatus: ["!=", "0"] },
	orderBy: "creation desc",
	realtime: true,
	auto: true,
	cacheKey: "bookings-list",
	onError: console.error,
	transform(data) {
		return data.map((booking) => ({
			...booking,
			formatted_amount:
				booking.total_amount !== 0
					? formatCurrency(booking.total_amount, booking.currency)
					: __("FREE"),
			status: booking.status || __("Pending"),
			start_date: dayjsLocal(booking.start_date).format("MMM DD, YYYY"),
			ticket_count: pluralize(
				booking.attendees ? booking.attendees.length : 0,
				__("Ticket")
			),
		}));
	},
});
</script>
