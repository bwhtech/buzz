<script setup lang="ts">
import { Alert } from "frappe-ui"
import { Accordion } from "frappe-ui/experimental"
import { computed } from "vue"

import BookingSummary from "@/components/dashboard/events/BookingSummary.vue"
import BookingActions from "@/components/dashboard/tickets/BookingActions.vue"
import RegistrationRequestNotice from "@/components/RegistrationRequestNotice.vue"
import { useBookingSummary } from "@/data/bookings"
import { requestNotice } from "@/utils/registrationRequest"

// Fetched per booking rather than off the viewer's own bookings: the receipt behind a
// ticket somebody else paid for is still theirs to read.
const props = defineProps<{ booking: string; isBooker: boolean }>()

const summary = useBookingSummary(() => props.booking)

const accordionItems = [{ value: "booking", title: "Booking Details" }]

const STATUS_NOTICES = {
	"Approval Pending": {
		theme: "amber",
		title: "Payment Confirmation Pending",
		description:
			"Your booking is confirmed subject to verifying the offline payment details. You will be notified once payment is verified.",
	},
	Rejected: {
		theme: "red",
		title: "Booking Rejected",
		description:
			"Your booking has been rejected. Please contact the event organizer for more information.",
	},
} as const

// A registration request's state, with Pay now once a paid request is approved.
const request = computed(() => requestNotice(summary.data?.status))

// Only an offline payment waits on approval; an online one marked pending is still at the gateway.
const statusNotice = computed(() => {
	const row = summary.data
	if (!row) return null
	if (row.status === "Approval Pending" && !row.is_offline) return null
	return STATUS_NOTICES[row.status as keyof typeof STATUS_NOTICES] || null
})
</script>

<template>
	<div v-if="summary.data" class="space-y-3">
		<RegistrationRequestNotice v-if="request" :booking-id="booking" :notice="request" />
		<Alert v-else-if="statusNotice" v-bind="statusNotice" />
		<Accordion :items="accordionItems">
			<template #item-content>
				<BookingSummary :booking="summary.data" show-id />
			</template>
		</Accordion>
		<BookingActions v-if="isBooker" :booking="booking" />
	</div>
</template>
