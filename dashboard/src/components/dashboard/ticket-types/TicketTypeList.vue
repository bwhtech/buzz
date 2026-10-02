<script setup lang="ts">
import { dayjsLocal } from "frappe-ui"

import PricedItemRow from "@/components/common/PricedItemRow.vue"
import type { TicketTypeItem } from "@/types"

defineProps<{ ticketTypes: TicketTypeItem[]; canWrite?: boolean }>()
defineEmits<{ open: [name: string] }>()

const isSoldOut = (ticketType: TicketTypeItem) =>
	ticketType.max_tickets_available > 0 &&
	ticketType.tickets_sold >= ticketType.max_tickets_available

function badge(ticketType: TicketTypeItem) {
	if (!ticketType.is_published) return { label: "Disabled", theme: "red" as const }
	return isSoldOut(ticketType) ? { label: "Sold out", theme: "amber" as const } : null
}

function salesLabel(ticketType: TicketTypeItem) {
	if (!ticketType.auto_unpublish_after) return "No end date"
	return `Sales end ${dayjsLocal(ticketType.auto_unpublish_after).format("D MMM YYYY")}`
}

// A ticket type without a seat count sells any number of tickets.
function seatsLabel(ticketType: TicketTypeItem) {
	const seats = ticketType.max_tickets_available
	if (!seats) return `Unlimited · ${ticketType.tickets_sold} sold`
	return `${ticketType.tickets_sold} of ${seats} sold`
}
</script>

<template>
	<ul class="space-y-2">
		<li v-for="ticketType in ticketTypes" :key="ticketType.name">
			<PricedItemRow
				:title="ticketType.title"
				:subtitle="salesLabel(ticketType)"
				:prices="ticketType.prices"
				:usage-label="seatsLabel(ticketType)"
				:usage-percent="
					ticketType.max_tickets_available
						? (ticketType.tickets_sold / ticketType.max_tickets_available) * 100
						: null
				"
				:badge="badge(ticketType)"
				:muted="!ticketType.is_published"
				:disabled="!canWrite"
				@click="$emit('open', ticketType.name)"
			/>
		</li>
	</ul>
</template>
