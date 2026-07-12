<template>
	<BookingHeader :booking-id="bookingId" />

	<div class="w-4" v-if="bookingDetails.loading">
		<Spinner />
	</div>

	<div v-else-if="bookingDetails.data">
		<!-- Approval Pending Status -->
		<div
			v-if="!bookingDetails.data.event.free_webinar && isOfflinePaymentPending"
			class="mb-6"
		>
			<div class="p-4 rounded-lg border bg-yellow-50 border-yellow-200">
				<div class="flex items-center gap-3">
					<div
						class="w-8 h-8 rounded-full bg-yellow-100 flex items-center justify-center"
					>
						<LucideClock class="w-4 h-4 text-yellow-600" />
					</div>
					<div class="flex-1">
						<h3 class="font-semibold text-yellow-800">
							{{ __("Payment Confirmation Pending") }}
						</h3>
						<p class="text-sm text-yellow-700">
							{{
								__(
									"Your booking is confirmed subject to verifying the offline payment details. You will be notified once payment is verified.",
								)
							}}
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Rejected Status -->
		<div v-if="isBookingRejected" class="mb-6">
			<div class="p-4 rounded-lg border bg-red-50 border-red-200">
				<div class="flex items-center gap-3">
					<div class="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
						<LucideXCircle class="w-4 h-4 text-red-600" />
					</div>
					<div class="flex-1">
						<h3 class="font-semibold text-red-800">
							{{ __("Booking Rejected") }}
						</h3>
						<p class="text-sm text-red-700">
							{{
								__(
									"Your booking has been rejected. Please contact the event organizer for more information.",
								)
							}}
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Event Information and Payment Summary in two columns -->
		<div class="grid grid-cols-1 gap-6 mb-6"
			:class="{ 'lg:grid-cols-2': showPaymentSummary }"
		>
			<!-- Event Information -->
			<BookingEventInfo
				v-if="bookingDetails.data.event"
				:event="bookingDetails.data.event"
				:venue="bookingDetails.data.venue"
			/>

			<!-- Booking Financial Summary -->
			<BookingFinancialSummary
				v-if="!bookingDetails.data.event.free_webinar && showPaymentSummary"
				:booking="bookingDetails.data.doc"
			/>
		</div>

		<!-- Cancellation Request Section -->
		<!-- Only show if there's a pending cancellation request (not yet submitted/accepted) -->
		<CancellationRequestNotice
			v-if="!bookingDetails.data.event.free_webinar && hasPendingCancellationRequest"
			:cancellation-request="bookingDetails.data.cancellation_request"
		/>

		<!-- Tickets Section -->
		<TicketsSection
			v-if="!bookingDetails.data.event.free_webinar && !isOfflinePaymentPending"
			:tickets="bookingDetails.data.tickets"
			:can-request-cancellation="canRequestCancellation"
			:can-transfer-tickets="canTransferTickets"
			:can-change-add-ons="canChangeAddOns"
			:cancellation-request="bookingDetails.data.cancellation_request"
			:cancellation-requested-tickets="bookingDetails.data.cancellation_requested_tickets"
			:cancelled-tickets="bookingDetails.data.cancelled_tickets"
			@request-cancellation="showCancellationDialog = true"
			@transfer-success="onTicketTransferSuccess"
		/>

		<CancellationRequestDialog
			v-if="!isOfflinePaymentPending"
			v-model="showCancellationDialog"
			:tickets="bookingDetails.data.tickets"
			:booking-id="bookingId"
			:cancellation-requested-tickets="bookingDetails.data.cancellation_requested_tickets"
			:cancelled-tickets="bookingDetails.data.cancelled_tickets"
			@success="onCancellationRequestSuccess"
		/>
	</div>
</template>

<script setup>
import { useBookingFormStorage } from "@/composables/useBookingFormStorage";
import { usePaymentSuccess } from "@/composables/usePaymentSuccess";
import { Spinner, createResource } from "frappe-ui";
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import LucideClock from "~icons/lucide/clock";
import LucideXCircle from "~icons/lucide/x-circle";
import BookingEventInfo from "../components/BookingEventInfo.vue";
import BookingFinancialSummary from "../components/BookingFinancialSummary.vue";
import BookingHeader from "../components/BookingHeader.vue";
import CancellationRequestDialog from "../components/CancellationRequestDialog.vue";
import CancellationRequestNotice from "../components/CancellationRequestNotice.vue";
import SuccessMessage from "../components/SuccessMessage.vue";
import TicketsSection from "../components/TicketsSection.vue";

const route = useRoute();

const props = defineProps({
	bookingId: {
		type: String,
		required: true,
	},
});

// Check if this is an offline payment that is not yet verified
const isOfflinePaymentPending = computed(() => {
	return bookingDetails.data?.doc?.status === "Approval Pending";
});

const isBookingRejected = computed(() => {
	return bookingDetails.data?.doc?.status === "Rejected";
});

// Hide the payment summary for free bookings (total_amount == 0)
const showPaymentSummary = computed(() => {
	const doc = bookingDetails.data?.doc;
	return doc && (doc.total_amount || 0) > 0;
});

// Check if this is a successful payment redirect (check URL immediately)
const isPaymentSuccess = route.query.success === "true";
const isConfirmationPending = route.query.offline === "true";

// Use payment success composable for UI effects (confetti, message, URL cleanup)
// Disable confetti when booking is pending approval (e.g. offline payments)
const { showSuccessMessage } = usePaymentSuccess({
	enableConfetti: !isConfirmationPending,
});

const showCancellationDialog = ref(false);

const bookingDetails = createResource({
	url: "buzz.api.get_booking_details",
	params: { booking_id: props.bookingId },
	auto: true,
	onSuccess: (data) => {
		// Clear stored booking form data if this was a successful payment
		if (isPaymentSuccess && data?.event?.route) {
			const { clearStoredData } = useBookingFormStorage(data.event.route);
			clearStoredData();
		}
	},
});

const canTransferTickets = computed(() => {
	return bookingDetails.data?.can_transfer_ticket?.can_transfer || false;
});

const canChangeAddOns = computed(() => {
	return bookingDetails.data?.can_change_add_ons?.can_change_add_ons || false;
});

const canRequestCancellation = computed(() => {
	return bookingDetails.data?.can_request_cancellation?.can_request_cancellation || false;
});

// Only show cancellation notice if there's a pending request (not yet submitted)
const hasPendingCancellationRequest = computed(() => {
	const cancellationRequest = bookingDetails.data?.cancellation_request;
	const cancellationRequestedTickets = bookingDetails.data?.cancellation_requested_tickets || [];

	// Show notice only if there's a cancellation request AND there are tickets with pending cancellation
	return cancellationRequest && cancellationRequestedTickets.length > 0;
});

const onTicketTransferSuccess = () => {
	bookingDetails.reload();
};

const onCancellationRequestSuccess = (data) => {
	bookingDetails.reload();
};
</script>
