<script setup lang="ts">
import { computed } from "vue"

import PrintedTicket from "@/components/dashboard/tickets/PrintedTicket.vue"
import type { TicketWithEvent } from "@/types"

import type { StepEvent } from "../setupSteps"

// The ticket guests get, one per ticket type, fanned down and to the right so the
// stack runs off the card. Empty: a single blank ticket, faded, where the first goes.
const props = defineProps<{ done: boolean; event: StepEvent }>()

const TYPES = ["Speaker pass", "Student", "General"]

const tickets = computed<TicketWithEvent[]>(() =>
	(props.done ? TYPES : ["Ticket type"]).map((type, index) => ({
		name: `BZ-04${21 + index}`,
		attendee_name: "Guest",
		attendee_email: null,
		ticket_type: type,
		qr_code: null,
		booking: null,
		event_title: props.event.title,
		start_date: null,
		start_time: null,
		end_date: null,
		venue: props.event.venue,
	})),
)
</script>

<template>
	<div class="mini-tickets" :data-empty="!done || undefined">
		<div
			v-for="(ticket, index) in tickets"
			:key="ticket.name"
			class="mini-ticket"
			:style="{ '--layer': tickets.length - 1 - index }"
		>
			<PrintedTicket :ticket="ticket" static />
		</div>
	</div>
</template>

<style scoped>
.mini-tickets {
	height: 150px;
}
/* The real ticket, laid out at full size and scaled, so it stays pixel-identical.
   Layer 0 is the front one; each step back sits higher and further right. */
.mini-ticket {
	position: absolute;
	left: 0;
	top: 0;
	width: 400px;
	scale: 0.6;
	transform-origin: 0 0;
	translate: calc(var(--layer) * 16px) calc(16px - var(--layer) * 14px);
	transition: translate 300ms cubic-bezier(0.23, 1, 0.32, 1);
	transition-delay: calc(var(--layer) * 30ms);
	pointer-events: none;
}
:global(.setup-card:is(:hover, :focus-within)) .mini-ticket {
	translate: calc(var(--layer) * 22px) calc(16px - var(--layer) * 18px);
}
.mini-tickets[data-empty] .mini-ticket {
	opacity: 0.45;
	filter: grayscale(1);
}
@media (prefers-reduced-motion: reduce) {
	.mini-ticket {
		transition: none;
	}
}
</style>
