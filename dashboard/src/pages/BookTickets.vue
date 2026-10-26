<template>
	<div>
		<!-- First load only: the availability poll must not unmount the form and drop its hold. -->
		<div
			v-if="eventBookingResource.loading && !eventBookingResource.data"
			class="flex justify-center py-16"
		>
			<Spinner class="w-8 h-8" />
		</div>
		<div v-else-if="eventNotFound" class="flex flex-col items-center justify-center py-16 px-4">
			<div class="text-center max-w-md">
				<h2 class="text-2xl-semibold text-ink-gray-8 mb-2">
					{{ __("Event Not Found") }}
				</h2>
				<p class="text-ink-gray-6 mb-6">
					{{ __("The event you are looking for does not exist or may have been removed.") }}
				</p>
				<Button variant="solid" size="lg" @click="$router.push('/')">{{ __("Go to Home") }}</Button>
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
					class="w-full rounded-6 mb-6 object-cover max-h-48"
				/>
				<h2 class="text-2xl-semibold text-ink-gray-8 mb-2">
					{{ __("Registrations Closed") }}
				</h2>
				<p class="text-ink-gray-6 mb-6">
					{{ __("Registrations for this event are closed.") }}
				</p>
				<Button variant="solid" size="lg" @click="goToHome">{{ __("Browse Other Events") }}</Button>
			</div>
		</div>
		<div
			v-else-if="!eventBookingData.availableTicketTypes?.length"
			class="flex flex-col items-center justify-center py-16 px-4"
		>
			<div class="text-center max-w-md">
				<h2 class="text-2xl-semibold text-ink-gray-8 mb-2">
					{{ __("No tickets available right now") }}
				</h2>
				<p class="text-ink-gray-6">
					{{
						__(
							"Some tickets may be held by people checking out. They come back if they don't finish, and this page updates when they do.",
						)
					}}
				</p>
			</div>
		</div>
		<div v-else>
			<BookingForm
				v-if="eventBookingData.availableAddOns && eventBookingData.availableTicketTypes"
				:availableAddOns="eventBookingData.availableAddOns"
				:availableTicketTypes="eventBookingData.availableTicketTypes"
				:ticketCategories="eventBookingData.ticketCategories"
				:taxSettings="eventBookingData.taxSettings || {}"
				:eventDetails="eventBookingData.eventDetails || {}"
				:customFields="eventBookingData.customFields || []"
				:logicRules="eventBookingData.logicRules"
				:coreFields="eventBookingData.coreFields"
				:success="eventBookingData.success"
				:eventRoute="eventRoute"
				:paymentGateways="eventBookingData.paymentGateways"
				:isGuestMode="isGuest"
				:offlineMethods="eventBookingData.offlineMethods"
				:changeAccessCode="changeAccessCode"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useIntervalFn } from "@vueuse/core"
import { Spinner, useCall, usePageMeta } from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"
import { useRoute } from "vue-router"

import type { CoreField } from "@/components/registration/coreFields"
import { holdTokenKey } from "@/composables/useTicketHold"
import { session } from "@/data/session"
import type {
	AvailableAddOn,
	AvailableTicketType,
	BookingTicketCategory,
	FrappeField,
	OfflineMethod,
} from "@/types"
import type { LogicRule } from "@/utils/formLogic"

import BookingForm from "../components/BookingForm.vue"

const AVAILABILITY_POLL_MS = 20_000

const eventBookingData = reactive<{
	availableAddOns: AvailableAddOn[] | null
	availableTicketTypes: AvailableTicketType[] | null
	ticketCategories: BookingTicketCategory[]
	taxSettings: Record<string, any> | null
	eventDetails: Record<string, any> | null
	customFields: FrappeField[] | null
	logicRules: Record<string, LogicRule[]>
	coreFields: Record<string, CoreField[]>
	success: { title?: string | null; message?: string | null }
	paymentGateways: string[]
	offlineMethods: OfflineMethod[]
}>({
	availableAddOns: null,
	availableTicketTypes: null,
	ticketCategories: [],
	taxSettings: null,
	eventDetails: null,
	customFields: null,
	logicRules: {},
	coreFields: {},
	success: {},
	paymentGateways: [],
	offlineMethods: [],
})

const eventNotFound = ref(false)
const registrationsClosed = ref(false)

const props = defineProps({
	eventRoute: {
		type: String,
		required: true,
	},
})

const accessCode = ref(String(useRoute().query.code ?? ""))

const isGuest = computed(() => !session.isLoggedIn)

usePageMeta(() => {
	const eventTitle = eventBookingData.eventDetails?.title
	return eventTitle ? { title: `${__("Register")} | ${eventTitle}` } : null
})

const goToHome = () => {
	window.location.href = "/"
}

// The form's own hold counts as available, so a reload still lists the tickets it holds.
const bookingDataParams = () => {
	const holdToken = sessionStorage.getItem(holdTokenKey(props.eventRoute))
	return {
		event_route: props.eventRoute,
		...(holdToken ? { hold_token: holdToken } : {}),
		...(accessCode.value ? { access_code: accessCode.value } : {}),
	}
}

const eventBookingResource = useCall<
	Record<string, any>,
	{ event_route: string; hold_token?: string; access_code?: string }
>({
	url: "/api/v2/method/buzz.api.booking.get_event_booking_data",
	params: bookingDataParams,
	onSuccess: (data) => {
		eventBookingData.availableAddOns = data.available_add_ons || []
		// A ticket type's first price row is its default price.
		eventBookingData.availableTicketTypes = (data.available_ticket_types || []).map(
			(ticketType: AvailableTicketType) => ({
				...ticketType,
				price: ticketType.prices?.[0]?.price ?? 0,
				currency: ticketType.prices?.[0]?.currency,
			}),
		)
		eventBookingData.ticketCategories = data.ticket_categories || []
		eventBookingData.taxSettings = data.tax_settings || {
			apply_tax: false,
			tax_inclusive: false,
			tax_label: "Tax",
			tax_percentage: 0,
		}
		eventBookingData.eventDetails = data.event_details || {}
		eventBookingData.customFields = data.custom_fields || []
		eventBookingData.logicRules = data.logic_rules || {}
		eventBookingData.coreFields = data.core_fields || {}
		eventBookingData.success = data.success || {}
		eventBookingData.paymentGateways = data.payment_gateways || []
		eventBookingData.offlineMethods = data.offline_methods || []
		registrationsClosed.value = data.registrations_closed || false
		// The form shows the error when it validates the code itself.
		if (data.access_code?.error) accessCode.value = ""
	},
	onError: (error) => {
		if (error.message.includes("DoesNotExistError")) {
			eventNotFound.value = true
		}
	},
})

function changeAccessCode(code: string) {
	accessCode.value = code
	return eventBookingResource.reload()
}

// Other people's holds come and go, so the ticket types on offer are refreshed.
useIntervalFn(() => {
	if (document.visibilityState === "visible") eventBookingResource.reload()
}, AVAILABILITY_POLL_MS)

watch(
	() => session.isLoggedIn,
	(isLoggedIn) => {
		if (isLoggedIn) {
			eventBookingResource.reload()
		}
	},
)
</script>
