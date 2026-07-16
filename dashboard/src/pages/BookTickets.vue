<template>
	<div>
		<div v-if="eventBookingResource.loading" class="flex justify-center py-16">
			<Spinner class="w-8 h-8" />
		</div>
		<div
			v-else-if="eventNotFound"
			class="flex flex-col items-center justify-center py-16 px-4"
		>
			<div class="text-center max-w-md">
				<h2 class="text-xl font-semibold text-ink-gray-8 mb-2">
					{{ __("Event Not Found") }}
				</h2>
				<p class="text-ink-gray-6 mb-6">
					{{
						__(
							"The event you are looking for does not exist or may have been removed."
						)
					}}
				</p>
				<Button variant="solid" size="lg" @click="$router.push('/')">{{
					__("Go to Home")
				}}</Button>
			</div>
		</div>
		<div
			v-else-if="registrationsClosed"
			class="flex flex-col items-center justify-center py-16 px-4"
		>
			<div class="text-center max-w-md">
				<img
					v-if="eventBookingData.eventDetails?.banner_image"
					:src="eventBookingData.eventDetails.banner_image"
					:alt="eventBookingData.eventDetails?.title"
					class="w-full rounded-lg mb-6 object-cover max-h-48"
				/>
				<h2 class="text-xl font-semibold text-ink-gray-8 mb-2">
					{{ __("Registrations Closed") }}
				</h2>
				<p class="text-ink-gray-6 mb-6">
					{{ __("Registrations for this event are closed.") }}
				</p>
				<Button variant="solid" size="lg" @click="goToHome">{{
					__("Browse Other Events")
				}}</Button>
			</div>
		</div>
		<div v-else>
			<BookingForm
				v-if="eventBookingData.availableAddOns && eventBookingData.availableTicketTypes"
				:availableAddOns="eventBookingData.availableAddOns"
				:availableTicketTypes="eventBookingData.availableTicketTypes"
				:taxSettings="eventBookingData.taxSettings || {}"
				:eventDetails="eventBookingData.eventDetails || {}"
				:customFields="eventBookingData.customFields || []"
				:eventRoute="eventRoute"
				:paymentGateways="eventBookingData.paymentGateways"
				:isGuestMode="isGuest"
				:offlineMethods="eventBookingData.offlineMethods"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type {
	AvailableAddOn,
	AvailableTicketType,
	FrappeError,
	FrappeField,
	OfflineMethod,
} from "@/types";
import { session } from "@/data/session";
import { Spinner, createResource } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import BookingForm from "../components/BookingForm.vue";

const eventBookingData = reactive<{
	availableAddOns: AvailableAddOn[] | null;
	availableTicketTypes: AvailableTicketType[] | null;
	taxSettings: Record<string, any> | null;
	eventDetails: Record<string, any> | null;
	customFields: FrappeField[] | null;
	paymentGateways: any[];
	offlineMethods: OfflineMethod[];
}>({
	availableAddOns: null,
	availableTicketTypes: null,
	taxSettings: null,
	eventDetails: null,
	customFields: null,
	paymentGateways: [],
	offlineMethods: [],
});

const eventNotFound = ref(false);
const registrationsClosed = ref(false);

const props = defineProps({
	eventRoute: {
		type: String,
		required: true,
	},
});

const isGuest = computed(() => !session.isLoggedIn);

const goToHome = () => {
	window.location.href = "/";
};

const eventBookingResource = createResource({
	url: "buzz.api.get_event_booking_data",
	params: {
		event_route: props.eventRoute,
	},
	auto: true,
	onSuccess: (data: any) => {
		eventBookingData.availableAddOns = data.available_add_ons || [];
		eventBookingData.availableTicketTypes = data.available_ticket_types || [];
		eventBookingData.taxSettings = data.tax_settings || {
			apply_tax: false,
			tax_inclusive: false,
			tax_label: "Tax",
			tax_percentage: 0,
		};
		eventBookingData.eventDetails = data.event_details || {};
		eventBookingData.customFields = data.custom_fields || [];
		eventBookingData.paymentGateways = data.payment_gateways || [];
		eventBookingData.offlineMethods = data.offline_methods || [];
		registrationsClosed.value = data.registrations_closed || false;
	},
	onError: (error: FrappeError) => {
		if (error.message?.includes("DoesNotExistError")) {
			eventNotFound.value = true;
		}
	},
});

watch(
	() => session.isLoggedIn,
	(isLoggedIn) => {
		if (isLoggedIn) {
			eventBookingResource.reload();
		}
	}
);
</script>
