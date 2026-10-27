<template>
	<div class="flex justify-center items-center py-8" v-if="confirmation.loading">
		<Spinner />
	</div>

	<div v-else-if="confirmation.data" class="mx-auto flex max-w-[600px] flex-col gap-9 pb-16">
		<div class="flex flex-col gap-7">
			<SuccessHero
				:event-title="event.title"
				:ticket-count="confirmation.data.tickets.length"
				:title="confirmation.data.success?.title"
				:note="safeMarkdown(confirmation.data.success?.message)"
			/>

			<EventSummaryCard
				class="fade-up-in"
				style="animation-delay: 160ms"
				:event="event"
				:venue="confirmation.data.venue"
				:booking-id="bookingId"
			/>

			<div class="fade-up-in flex flex-wrap justify-center gap-2" style="animation-delay: 220ms">
				<Button
					size="md"
					variant="solid"
					icon-left="lucide-calendar-plus"
					:label="__('Add to calendar')"
					:href="bookingFileUrl('get_calendar_invite')"
				/>
				<Button
					v-if="confirmation.data.venue?.map_link"
					size="md"
					variant="subtle"
					icon-left="lucide-navigation"
					:label="__('Get directions')"
					:href="confirmation.data.venue.map_link"
				/>
				<Button
					v-if="event.route"
					size="md"
					variant="subtle"
					icon-left="lucide-link"
					:label="__('Invite a friend')"
					@click="copyToClipboard(eventUrl(event.route), __('Event link copied'))"
				/>
			</div>
		</div>

		<TicketRows
			class="fade-up-in"
			style="animation-delay: 260ms"
			:tickets="confirmation.data.tickets"
			:download-url="bookingFileUrl('download_tickets')"
		/>

		<BookingFinancialSummary
			v-if="showPaymentSummary"
			class="fade-up-in"
			style="animation-delay: 340ms"
			:booking="confirmation.data.booking"
		>
			<template #footer>{{ paymentLine }}</template>
		</BookingFinancialSummary>

		<p class="fade-up-in text-center text-p-sm text-ink-gray-5" style="animation-delay: 400ms">
			{{ __("Need to change a name or cancel?") }}
			<RouterLink
				v-if="session.isLoggedIn"
				:to="`/account/bookings/${bookingId}`"
				class="text-ink-gray-8 hover:underline"
			>
				{{ __("Manage booking") }}
			</RouterLink>
			<button v-else class="text-ink-gray-8 hover:underline" @click="openLoginDialog()">
				{{ __("Log in to manage bookings") }}
			</button>
		</p>
	</div>

	<!-- Error / invalid token -->
	<div v-else-if="confirmation.error" class="text-center py-16">
		<h2 class="text-2xl-semibold text-ink-gray-9 mb-2">
			{{ __("Booking not found") }}
		</h2>
		<p class="text-ink-gray-6">
			{{ __("This confirmation link is invalid or has expired.") }}
		</p>
	</div>
</template>

<script setup lang="ts">
import { Button, Spinner, dayjsLocal, useCall } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import EventSummaryCard from "@/components/booking-success/EventSummaryCard.vue"
import SuccessHero from "@/components/booking-success/SuccessHero.vue"
import TicketRows from "@/components/booking-success/TicketRows.vue"
import BookingFinancialSummary from "@/components/BookingFinancialSummary.vue"
import { useBookingFormStorage } from "@/composables/useBookingFormStorage"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import { useLoginDialog } from "@/composables/useLoginDialog"
import { session } from "@/data/session"
import { triggerCelebrationConfetti } from "@/utils/confetti"
import { eventUrl } from "@/utils/eventUrl"
import { safeMarkdown } from "@/utils/markdown"

const props = defineProps({
	bookingId: {
		type: String,
		required: true,
	},
})

const route = useRoute()
const { open: openLoginDialog } = useLoginDialog()
const copyToClipboard = useCopyToClipboard()

const confirmation = useCall<Record<string, any>, Record<string, unknown>>({
	url: "/api/v2/method/buzz.api.booking.get_booking_confirmation",
	params: { booking_id: props.bookingId, token: route.query.token },
	onSuccess: (data) => {
		triggerCelebrationConfetti()
		if (data?.event?.route) {
			const { clearStoredData } = useBookingFormStorage(data.event.route)
			clearStoredData()
		}
	},
})

const event = computed(() => confirmation.data!.event)

// Files the confirmation hands out; a guest proves access with the page's own token.
function bookingFileUrl(method: string) {
	const params = new URLSearchParams({ booking_id: props.bookingId })
	if (route.query.token) params.set("token", String(route.query.token))
	return `/api/v2/method/buzz.api.booking.${method}?${params}`
}

const paymentLine = computed(() => {
	const { payment_method, booked_on } = confirmation.data!.booking
	const bookedOn = dayjsLocal(booked_on).format("MMM D, YYYY, h:mm A")
	return [payment_method, bookedOn].filter(Boolean).join(" · ")
})

const showPaymentSummary = computed(() => (confirmation.data?.booking.total_amount || 0) > 0)
</script>
