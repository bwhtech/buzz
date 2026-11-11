<script setup lang="ts">
import { Alert, Button } from "frappe-ui"
import { computed, ref } from "vue"

import AddOnPreferenceDialog from "@/components/AddOnPreferenceDialog.vue"
import CheckInQrDialog from "@/components/dashboard/tickets/CheckInQrDialog.vue"
import PrintedTicket from "@/components/dashboard/tickets/PrintedTicket.vue"
import TicketBookingDetails from "@/components/dashboard/tickets/TicketBookingDetails.vue"
import TicketTransferDialog from "@/components/TicketTransferDialog.vue"
import { useTicketDetails } from "@/data/tickets"
import type { TicketWithEvent } from "@/types"
import { ticketPdfUrl } from "@/utils/ticketPdf"

const props = defineProps<{ ticket: TicketWithEvent; showReceipt: boolean; isBooker: boolean }>()

// A transfer hands the ticket to someone else, so the list it came from has to reload.
const emit = defineEmits<{ transferred: [] }>()

const details = useTicketDetails(() => props.ticket.name)

const qrDialogOpen = ref(false)
const transferDialogOpen = ref(false)
const addOnDialogOpen = ref(false)

const addOns = computed(() => details.data?.add_ons || [])
const hasCustomizableAddOns = computed(() => addOns.value.some((addOn) => addOn.options?.length))
const canChangeAddOns = computed(
	() => hasCustomizableAddOns.value && details.data?.can_change_add_ons,
)
const addOnWindowClosed = computed(
	() => hasCustomizableAddOns.value && details.data && !details.data.can_change_add_ons,
)

const downloadUrl = computed(() =>
	ticketPdfUrl(props.ticket.name, details.data?.event.ticket_print_format),
)
</script>

<template>
	<div class="space-y-3">
		<div class="flex flex-wrap gap-2">
			<Button
				variant="outline"
				icon-left="lucide-qr-code"
				label="Ticket QR"
				tooltip="Show Check-In QR"
				@click="qrDialogOpen = true"
			/>
			<Button
				variant="outline"
				icon="lucide-download"
				aria-label="Download ticket"
				tooltip="Download ticket"
				:href="downloadUrl"
			/>
			<Button
				v-if="details.data?.can_transfer_ticket"
				variant="outline"
				icon-left="lucide-user-plus"
				label="Transfer"
				@click="transferDialogOpen = true"
			/>
			<Button
				v-if="canChangeAddOns"
				variant="outline"
				icon-left="lucide-pencil"
				label="Add-ons"
				@click="addOnDialogOpen = true"
			/>
			<Button
				v-if="details.data?.zoom_join_url"
				variant="solid"
				icon-right="lucide-arrow-up-right"
				label="Join Webinar"
				:href="details.data.zoom_join_url"
			/>
		</div>
		<Alert
			v-if="addOnWindowClosed"
			theme="amber"
			title="Add-on preference changes are no longer available"
			description="The change window has closed as the event is approaching."
		/>
		<PrintedTicket :ticket="ticket" class="-rotate-1" static />
		<TicketBookingDetails v-if="showReceipt" :booking="ticket.booking!" :is-booker="isBooker" />

		<CheckInQrDialog
			v-model:open="qrDialogOpen"
			:qr-code="ticket.qr_code"
			:attendee-name="ticket.attendee_name"
			:attendee-email="ticket.attendee_email"
			:ticket-type="ticket.ticket_type"
			:event-title="ticket.event_title"
			:add-ons="addOns"
		/>
		<TicketTransferDialog
			v-model="transferDialogOpen"
			:ticket="ticket"
			@success="emit('transferred')"
		/>
		<AddOnPreferenceDialog
			v-if="details.data"
			v-model="addOnDialogOpen"
			:ticket="{ attendee_name: ticket.attendee_name, add_ons: addOns }"
			@success="details.reload()"
		/>
	</div>
</template>
