<template>
	<div class="w-4" v-if="confirmation.loading">
		<Spinner />
	</div>

	<div v-else-if="confirmation.data">
		<!-- Success message + confetti -->
		<SuccessMessage
			:show="showSuccessMessage"
			:is-webinar="confirmation.data.event.free_webinar"
		/>

		<!-- Event Information and Payment Summary in two columns -->
		<div class="grid grid-cols-1 gap-6 mb-6" :class="{ 'lg:grid-cols-2': showPaymentSummary }">
			<BookingEventInfo :event="confirmation.data.event" :venue="confirmation.data.venue" />

			<BookingFinancialSummary
				v-if="showPaymentSummary"
				:booking="confirmation.data.booking"
			/>
		</div>

		<!-- Tickets (read-only) -->
		<TicketsSection
			:tickets="confirmation.data.tickets"
			:can-request-cancellation="false"
			:can-transfer-tickets="false"
			:can-change-add-ons="false"
		/>

		<!-- Manage bookings CTA -->
		<div class="mt-6 flex justify-center">
			<Button v-if="!session.isLoggedIn" variant="outline" @click="openLoginDialog()">
				{{ __("Log in to manage bookings") }}
			</Button>
			<Button v-else variant="outline" :link="`/dashboard/account/bookings/${bookingId}`">
				{{ __("Manage booking") }}
			</Button>
		</div>
	</div>

	<!-- Error / invalid token -->
	<div v-else-if="confirmation.error" class="text-center py-16">
		<h2 class="text-xl font-semibold text-ink-gray-9 mb-2">
			{{ __("Booking not found") }}
		</h2>
		<p class="text-ink-gray-6">
			{{ __("This confirmation link is invalid or has expired.") }}
		</p>
	</div>
</template>

<script setup>
import { useBookingFormStorage } from "@/composables/useBookingFormStorage";
import { useLoginDialog } from "@/composables/useLoginDialog";
import { usePaymentSuccess } from "@/composables/usePaymentSuccess";
import { session } from "@/data/session";
import { Button, Spinner, createResource } from "frappe-ui";
import { computed } from "vue";
import { useRoute } from "vue-router";
import BookingEventInfo from "../components/BookingEventInfo.vue";
import BookingFinancialSummary from "../components/BookingFinancialSummary.vue";
import SuccessMessage from "../components/SuccessMessage.vue";
import TicketsSection from "../components/TicketsSection.vue";

const props = defineProps({
	bookingId: {
		type: String,
		required: true,
	},
});

const route = useRoute();
const { open: openLoginDialog } = useLoginDialog();

// Confetti + success message, always on for this page. Keep the token in the
// URL (cleanupUrl: false) so a refresh can still re-fetch the booking.
const { showSuccessMessage, showSuccess } = usePaymentSuccess({
	enableConfetti: true,
	cleanupUrl: false,
});

const showPaymentSummary = computed(() => {
	const booking = confirmation.data?.booking;
	return booking && (booking.total_amount || 0) > 0;
});

const confirmation = createResource({
	url: "buzz.api.get_booking_confirmation",
	params: { booking_id: props.bookingId, token: route.query.token },
	auto: true,
	onSuccess: (data) => {
		showSuccess();
		// Clear any stored booking form data now that the booking is confirmed
		if (data?.event?.route) {
			const { clearStoredData } = useBookingFormStorage(data.event.route);
			clearStoredData();
		}
	},
});
</script>
