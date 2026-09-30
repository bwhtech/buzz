<template>
	<div>
		<ListView
			v-if="bookings.data"
			:columns="columns"
			:rows="bookings.data"
			row-key="name"
			:options="{
				selectable: false,
				getRowRoute: (row: Record<string, any>) => ({
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
								? 'amber'
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

<script setup lang="ts">
import { Badge, useCall } from "frappe-ui"
import { dayjsLocal } from "frappe-ui"
import { ListRowItem, ListView } from "frappe-ui/experimental"

import { formatCurrency } from "@/utils/currency"
import { pluralize } from "@/utils/pluralize"

const columns = [
	{ label: __("Event"), key: "event_title", width: "220px" },
	{ label: "", key: "ticket_count", width: "90px" },
	{ label: __("Start Date"), key: "start_date", width: "110px" },
	{ label: __("Venue"), key: "venue", width: "140px" },
	{ label: __("Amount Paid"), key: "formatted_amount", width: "110px" },
	{ label: __("Status"), key: "status", width: "120px" },
]

const bookings = useCall<any[]>({
	url: "/api/v2/method/buzz.api.booking.get_my_bookings",
	onError: console.error,
	transform(data: any[]) {
		return data.map((booking: Record<string, any>) => ({
			...booking,
			formatted_amount:
				booking.total_amount !== 0
					? formatCurrency(booking.total_amount, booking.currency)
					: __("FREE"),
			status: booking.status || __("Pending"),
			start_date: dayjsLocal(booking.start_date).format("MMM DD, YYYY"),
			ticket_count: pluralize(booking.attendees ? booking.attendees.length : 0, __("Ticket")),
		}))
	},
})
</script>
