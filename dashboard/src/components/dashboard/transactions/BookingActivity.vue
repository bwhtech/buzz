<script setup lang="ts">
import { computed } from "vue"

import RecordActivity from "@/components/dashboard/comments/RecordActivity.vue"
import type { EmailAttachmentChoice } from "@/data/comments"
import type { TransactionDetail } from "@/types"
import { bookingStatusTheme } from "@/utils/transactionStatus"

const props = defineProps<{ transaction: TransactionDetail; canAttachInvoice: boolean }>()

const recipients = computed(() => {
	const { name, email } = props.transaction.buyer
	return email ? [{ name: name || email, email }] : []
})

// What the booking renders as PDFs, so nobody downloads a file only to upload it again.
const attachmentChoices = computed<EmailAttachmentChoice[]>(() => {
	const { name, tickets } = props.transaction
	return [
		...(props.canAttachInvoice
			? [
					{
						key: "invoice",
						label: "Invoice",
						fileName: `Invoice-${name}.pdf`,
						icon: "lucide-file-text",
						source: { kind: "invoice" as const },
					},
				]
			: []),
		...(tickets.length > 1
			? [
					{
						key: "tickets",
						label: `All ${tickets.length} tickets`,
						fileName: `Tickets-${name}.pdf`,
						icon: "lucide-tickets",
						source: { kind: "tickets" as const },
					},
				]
			: []),
		...tickets.map((ticket) => ({
			key: ticket.name,
			label: `Ticket · ${ticket.attendee_name || ticket.attendee_email || ticket.name}`,
			fileName: `Ticket-${ticket.name}.pdf`,
			icon: "lucide-ticket",
			source: { kind: "ticket" as const, ticket: ticket.name },
		})),
	]
})
</script>

<template>
	<RecordActivity
		doctype="Event Booking"
		:name="transaction.name"
		:recipients="recipients"
		:attachment-choices="attachmentChoices"
		:change-theme="bookingStatusTheme"
		created-label="booked"
	>
		<slot />
	</RecordActivity>
</template>
