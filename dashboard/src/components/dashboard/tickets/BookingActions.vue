<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed, ref } from "vue"

import CancellationRequestDialog from "@/components/CancellationRequestDialog.vue"
import CancellationRequestNotice from "@/components/CancellationRequestNotice.vue"
import { useBookingDetails } from "@/data/bookings"

// What only the booker can do with a booking: fetch its invoice and ask to cancel it.
const props = defineProps<{ booking: string }>()

const details = useBookingDetails(() => props.booking)

const cancellationDialogOpen = ref(false)

const invoiceUrl = computed(() => {
	if (!details.data?.invoice_available) return undefined
	return `/api/v2/method/buzz.api.booking.download_invoice?booking_id=${encodeURIComponent(props.booking)}`
})

const isPaidAndSubmitted = computed(
	() => details.data && !details.data.event.free_event && details.data.doc.docstatus === 1,
)

const hasPendingCancellation = computed(() =>
	Boolean(details.data?.cancellation_request && details.data.cancellation_requested_tickets.length),
)

const canRequestCancellation = computed(() => {
	const data = details.data
	if (!isPaidAndSubmitted.value || !data?.can_request_cancellation) return false
	const excluded = [...data.cancelled_tickets, ...data.cancellation_requested_tickets]
	return data.tickets.some((ticket) => !excluded.includes(ticket.name))
})
</script>

<template>
	<div v-if="details.data" class="space-y-3">
		<CancellationRequestNotice
			v-if="isPaidAndSubmitted && hasPendingCancellation"
			:cancellation-request="details.data.cancellation_request"
		/>
		<div v-if="invoiceUrl || canRequestCancellation" class="flex flex-wrap gap-2">
			<Button
				v-if="invoiceUrl"
				variant="outline"
				icon-left="lucide-file-text"
				label="Download Invoice"
				:href="invoiceUrl"
			/>
			<Button
				v-if="canRequestCancellation"
				variant="outline"
				icon-left="lucide-circle-x"
				label="Request Cancellation"
				@click="cancellationDialogOpen = true"
			/>
		</div>
		<CancellationRequestDialog
			v-if="canRequestCancellation"
			v-model="cancellationDialogOpen"
			:tickets="details.data.tickets"
			:booking-id="booking"
			:cancellation-requested-tickets="details.data.cancellation_requested_tickets"
			:cancelled-tickets="details.data.cancelled_tickets"
			@success="details.reload()"
		/>
	</div>
</template>
