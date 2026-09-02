<script setup lang="ts">
import { Button, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"

import CheckInQrDialog from "@/components/dashboard/tickets/CheckInQrDialog.vue"
import PrintedTicket from "@/components/dashboard/tickets/PrintedTicket.vue"
import TicketBookingDetails from "@/components/dashboard/tickets/TicketBookingDetails.vue"
import { useMyTickets, useTicketDetails } from "@/data/tickets"
import { userResource } from "@/data/user"
import type { MyEvent, TicketWithEvent } from "@/types"
import { ticketPdfUrl } from "@/utils/ticketPdf"

const props = defineProps<{ event: MyEvent }>()

const tickets = useMyTickets(() => props.event.name)

// A ticket whose event columns did not come over the link hop has nothing to print.
const myTickets = computed(() =>
	(tickets.data || []).filter((ticket): ticket is TicketWithEvent =>
		Boolean(ticket.start_date && ticket.event_title),
	),
)

// The feed row already says the viewer holds a ticket, so the section can hold its place
// while the ticket call is still out and the drawer stops jumping.
const ticketsPending = computed(
	() => Boolean(props.event.is_attendee) && tickets.loading && !myTickets.value.length,
)

const hasTickets = computed(() => Boolean(myTickets.value.length || ticketsPending.value))

// Several tickets can share one booking; the receipt goes under the first of them rather
// than repeating, call and all, beneath every ticket.
function ownsBookingReceipt(ticket: TicketWithEvent, index: number) {
	if (!ticket.booking) return false
	return myTickets.value.findIndex((row) => row.booking === ticket.booking) === index
}

// Held past the close so the dialog keeps its contents while it animates out.
const selectedTicket = ref<TicketWithEvent | null>(null)
const qrDialogOpen = ref(false)

// The stub the feed loads carries no add-on rows, so the dialog fetches them for
// whichever ticket was picked.
const ticketDetails = useTicketDetails(() => selectedTicket.value?.name)

function showCheckInQr(ticket: TicketWithEvent) {
	selectedTicket.value = ticket
	qrDialogOpen.value = true
}

const greeting = computed(() => {
	const name = userResource.data?.first_name || userResource.data?.full_name
	return name ? `You're in, ${name}` : "You're in"
})
</script>

<template>
	<div v-if="hasTickets" class="space-y-3 rounded-6 bg-surface-gray-1 p-4">
		<h3 class="flex items-center gap-2 text-xl font-semibold text-ink-gray-7">
			{{ greeting }}
		</h3>

		<div v-if="ticketsPending" class="space-y-3">
			<div class="flex gap-2">
				<Skeleton class="h-7 w-28 rounded-md" />
				<Skeleton class="h-7 w-7 rounded-md" />
			</div>
			<Skeleton class="h-40 w-full rounded-6" />
		</div>

		<template v-else>
			<div v-for="(ticket, index) in myTickets" :key="ticket.name" class="space-y-3">
				<div class="flex gap-2">
					<Button
						variant="outline"
						icon-left="lucide-qr-code"
						label="Ticket QR"
						tooltip="Show Check-In QR"
						@click="showCheckInQr(ticket)"
					/>
					<Button
						variant="outline"
						icon="lucide-download"
						aria-label="Download ticket"
						tooltip="Download ticket"
						:link="ticketPdfUrl(ticket.name)"
					/>
				</div>
				<PrintedTicket :ticket="ticket" class="-rotate-1" static />
				<TicketBookingDetails v-if="ownsBookingReceipt(ticket, index)" :booking="ticket.booking!" />
			</div>
		</template>

		<CheckInQrDialog
			v-if="selectedTicket"
			v-model:open="qrDialogOpen"
			:qr-code="selectedTicket.qr_code"
			:attendee-name="selectedTicket.attendee_name"
			:attendee-email="selectedTicket.attendee_email"
			:ticket-type="selectedTicket.ticket_type"
			:event-title="selectedTicket.event_title"
			:add-ons="ticketDetails.data?.add_ons"
		/>
	</div>
</template>
