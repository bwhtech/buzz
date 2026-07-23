<template>
	<div class="bg-surface-elevation-1 border border-outline-gray-1 rounded-lg p-6">
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-lg-semibold text-ink-gray-9">{{ __("Your Tickets") }}</h3>

			<!-- Request Cancellation Button -->
			<Button
				v-if="showCancellationButton"
				variant="subtle"
				@click="$emit('request-cancellation')"
			>
				{{
					cancellationRequest
						? __("Request More Cancellations")
						: __("Request Cancellation")
				}}
			</Button>
		</div>

		<!-- Tickets Grid -->
		<ol class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			<TicketCard
				v-for="ticket in tickets"
				:key="ticket.name"
				:ticket="ticket"
				:can-transfer="canTransferTickets"
				:can-change-add-ons="canChangeAddOns"
				:is-cancellation-requested="isCancellationRequestedTicket(ticket.name)"
				:is-cancelled="isCancelledTicket(ticket.name)"
				@transfer-success="$emit('transfer-success')"
			/>
		</ol>
	</div>
</template>

<script setup lang="ts">
import type { EventTicket } from "@/types";
import { Button } from "frappe-ui";
import { computed, type PropType } from "vue";
import TicketCard from "./TicketCard.vue";

const props = defineProps({
	tickets: {
		type: Array as PropType<EventTicket[]>,
		required: true,
	},
	canRequestCancellation: {
		type: Boolean,
		default: false,
	},
	canTransferTickets: {
		type: Boolean,
		default: false,
	},
	canChangeAddOns: {
		type: Boolean,
		default: false,
	},
	cancellationRequest: {
		type: Object as PropType<Record<string, any> | null>,
		default: null,
	},
	cancellationRequestedTickets: {
		type: Array as PropType<string[]>,
		default: () => [],
	},
	cancelledTickets: {
		type: Array as PropType<string[]>,
		default: () => [],
	},
});

defineEmits(["request-cancellation", "transfer-success"]);

// Check if there are any tickets that can still be cancelled
const hasTicketsAvailableForCancellation = computed(() => {
	return props.tickets.some(
		(ticket) =>
			!props.cancelledTickets.includes(ticket.name ?? "") &&
			!props.cancellationRequestedTickets.includes(ticket.name ?? "")
	);
});

// Show cancellation button if:
// 1. Cancellation is allowed
// 2. Either there's no existing request OR there are still tickets available for cancellation
const showCancellationButton = computed(() => {
	return (
		props.canRequestCancellation &&
		(!props.cancellationRequest || hasTicketsAvailableForCancellation.value)
	);
});

const isCancellationRequestedTicket = (ticketId?: string) => {
	return props.cancellationRequestedTickets?.includes(ticketId ?? "") || false;
};

const isCancelledTicket = (ticketId?: string) => {
	return props.cancelledTickets?.includes(ticketId ?? "") || false;
};
</script>
