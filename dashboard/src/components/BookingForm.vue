<!-- BookingForm.vue -->
<template>
	<div>
		<EventDetailsHeader :event-details="eventDetails" />

		<!-- Payment Gateway Selection Dialog -->
		<PaymentGatewayDialog
			v-model:open="showGatewayDialog"
			:payment-gateways="paymentGateways"
			@gateway-selected="onGatewaySelected"
		/>

		<!-- OTP Verification Dialog for Guest Booking -->
		<Dialog
			v-model="showOtpModal"
			:title="isPhoneOtp ? __('Verify Your Phone') : __('Verify Your Email')"
			size="sm"
		>
			<p class="text-sm text-ink-gray-6 mb-4">
				{{ __("Enter the 6-digit code sent to") }}
				<strong>{{ isPhoneOtp ? guestPhone : guestEmail }}</strong>
			</p>
			<FormControl
				v-model="otpCode"
				type="text"
				maxlength="6"
				:label="__('Verification Code')"
				placeholder="123456"
				class="mb-3"
				@keyup.enter="submitWithOtp"
				@input="otpError = ''"
			/>
			<ErrorMessage :message="otpError" />
			<Button
				variant="ghost"
				size="sm"
				:loading="sendOtpResource.loading"
				:disabled="resendCooldown > 0"
				@click="resendOtp"
			>
				{{
					resendCooldown > 0
						? __("Resend code in {0}s", [resendCooldown])
						: __("Resend code")
				}}
			</Button>

			<template #actions>
				<div class="flex justify-end space-x-3">
					<Button variant="ghost" @click="clearOtpState">{{ __("Cancel") }}</Button>
					<Button
						variant="solid"
						:loading="processBooking.loading"
						@click="submitWithOtp"
					>
						{{ __("Verify & Book") }}
					</Button>
				</div>
			</template>
		</Dialog>

		<!-- Success State for Guest Booking -->
		<div v-if="bookingSuccess" class="text-center py-12 px-4">
			<div class="bg-green-50 border border-green-200 rounded-xl p-8 max-w-md mx-auto">
				<LucideCheckCircle class="w-16 h-16 text-green-500 mx-auto mb-4" />
				<h2 class="text-3xl-semibold text-green-800 mb-2">
					{{ isWebinar ? __("Registration Confirmed!") : __("Booking Confirmed!") }}
				</h2>
				<p class="text-green-700 mb-4">
					<template v-if="isWebinar">
						{{ __("You have been registered successfully.") }}
					</template>
					<template v-else>
						{{ __("Your tickets have been sent to") }}
						<strong>{{ guestEmail }}</strong>
					</template>
				</p>
				<p class="text-sm text-green-600 mb-6">
					<template v-if="isWebinar">
						{{ __("You will receive an invite at") }}
						<strong>{{ guestEmail }}</strong>
						{{ __("shortly.") }}
					</template>
					<template v-else-if="eventDetails.send_ticket_email">
						{{ __("Check your email for ticket details and QR codes.") }}
					</template>
				</p>
				<div class="space-y-3">
					<p class="text-xs text-ink-gray-5">
						{{ __("Want to manage your bookings?") }}
					</p>
					<Button variant="outline" @click="openLoginDialog()">
						{{ __("Log in to your account") }}
					</Button>
				</div>
			</div>
		</div>

		<form v-else @submit.prevent="submit">
			<!-- Offline Payment Dialog -->
			<OfflinePaymentDialog
				v-model:open="showOfflineDialog"
				:amount="finalTotal"
				:currency="totalCurrency"
				:offline-settings="activeOfflineSettings"
				:loading="processBooking.loading"
				:custom-fields="activeOfflineCustomFields"
				@submit="onOfflinePaymentSubmit"
				@cancel="showOfflineDialog = false"
			/>
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
				<!-- Left Side: Form Inputs -->
				<div class="lg:col-span-2">
					<!-- Guest Contact Section -->
					<div
						v-if="props.isGuestMode"
						class="bg-surface-base border border-outline-gray-3 rounded-xl p-4 md:p-6 mb-6 shadow-sm"
					>
						<h3 class="text-sm-semibold text-ink-gray-8 mb-4">
							{{ __("Your Details") }}
						</h3>
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
							<FormControl
								v-model="guestFirstName"
								type="text"
								:label="__('First Name')"
								:placeholder="__('Enter your first name')"
								required
								@blur="prefillAttendee('name')"
							/>
							<FormControl
								v-model="guestLastName"
								type="text"
								:label="__('Last Name')"
								:placeholder="__('Enter your last name')"
								:required="isWebinar"
								@blur="prefillAttendee('name')"
							/>
							<FormControl
								v-model="guestEmail"
								type="email"
								:label="__('Email Address')"
								:placeholder="__('Enter your email')"
								required
								@blur="prefillAttendee('email')"
							/>
							<FormControl
								v-if="props.eventDetails.guest_verification_method === 'Phone OTP'"
								v-model="guestPhone"
								type="tel"
								:label="__('Phone Number')"
								:placeholder="__('Enter your phone number')"
								required
							/>
						</div>
					</div>

					<!-- Booking-level Custom Fields -->
					<div
						v-if="bookingCustomFields.length > 0"
						class="bg-surface-base border border-outline-gray-3 rounded-xl p-4 md:p-6 mb-6 shadow-sm"
					>
						<CustomFieldsSection
							v-model="bookingCustomFieldsData"
							:custom-fields="bookingCustomFields"
							:title="__('Booking Information')"
						/>
					</div>

					<BillingDetails
						v-if="shouldApplyTax"
						v-model:invoice-requested="invoiceRequested"
						v-model:tax-id="taxId"
						v-model:billing-address="billingAddress"
						:tax-label="taxLabel"
					/>

					<AttendeeFormControl
						v-for="(attendee, index) in attendees"
						:key="attendee.id"
						:attendee="attendee"
						:index="index"
						:available-ticket-types="availableTicketTypes"
						:available-add-ons="availableAddOns"
						:custom-fields="ticketCustomFields"
						:show-remove="attendees.length > 1"
						:eventDetails="eventDetails"
						@remove="removeAttendee(index)"
					/>

					<!-- Add Attendee Button -->
					<div class="text-center mt-6">
						<Button
							variant="outline"
							size="lg"
							@click="addAttendee"
							class="w-full max-w-md border-dashed border-2 border-outline-gray-2 hover:border-outline-gray-3 text-ink-gray-7 hover:text-ink-gray-8 py-4"
						>
							+ {{ __("Add Another Attendee") }}
						</Button>
					</div>
				</div>

				<!-- Right Side: Coupon, Summary and Submit -->
				<div class="lg:col-span-1">
					<div class="sticky top-4 w-full">
						<!-- Coupon Code Section -->
						<div
							v-if="finalTotal > 0 || couponApplied"
							class="bg-surface-base border border-outline-gray-3 rounded-xl p-4 mb-4"
						>
							<h3
								class="text-xs-medium text-ink-gray-6 uppercase tracking-wide mb-2"
							>
								{{ __("Coupon Code") }}
							</h3>

							<!-- Input state -->
							<div v-if="!couponApplied" class="flex gap-2">
								<FormControl
									v-model="couponCode"
									:placeholder="__('Enter code')"
									:aria-label="__('Coupon code')"
									class="flex-1 uppercase"
									@keyup.enter="applyCoupon"
								/>
								<Button
									variant="outline"
									@click="applyCoupon"
									:loading="validateCoupon.loading"
								>
									{{ __("Apply") }}
								</Button>
							</div>

							<!-- Applied state -->
							<div v-else-if="couponData">
								<div
									class="inline-flex flex-col bg-green-50 border border-green-200 rounded-lg px-3 py-2"
								>
									<div class="flex items-center gap-2">
										<LucideCheck class="w-4 h-4 text-green-600" />
										<span class="text-green-700 text-sm-semibold">{{
											couponCode
										}}</span>
										<span
											v-if="couponData.coupon_type === 'Discount'"
											class="text-green-600 text-sm-medium"
										>
											{{
												couponData.discount_type === "Percentage"
													? couponData.discount_value + "% off"
													: formatPriceOrFree(
															couponData.discount_value,
															totalCurrency
													  ) + " off"
											}}
										</span>
										<Button
											variant="ghost"
											@click="removeCoupon"
											class="!p-1 !min-w-0 text-green-500 hover:text-red-500 hover:bg-red-50 ml-auto"
											:title="__('Remove')"
										>
											<LucideX class="w-3.5 h-3.5" />
										</Button>
									</div>
									<span
										v-if="
											couponData.coupon_type === 'Discount' &&
											couponData.discount_type === 'Percentage' &&
											(couponData.max_discount_amount ?? 0) > 0
										"
										class="text-xs text-green-600/70 ml-6"
									>
										save up to
										{{
											formatCurrency(
												couponData.max_discount_amount,
												totalCurrency
											)
										}}
									</span>
								</div>

								<!-- Free Tickets Details -->
								<div
									v-if="couponData?.coupon_type === 'Free Tickets'"
									class="mt-3 text-sm space-y-2"
								>
									<!-- Compact info grid -->
									<div class="grid grid-cols-2 gap-2 text-xs">
										<div class="bg-surface-gray-2 rounded px-2 py-1.5">
											<span class="text-ink-gray-5">{{ __("Ticket") }}</span>
											<div class="text-ink-gray-8 font-medium truncate">
												{{
													ticketTypesMap[couponData?.ticket_type ?? ""]
														?.title || couponData?.ticket_type
												}}
											</div>
										</div>
										<div class="bg-surface-gray-2 rounded px-2 py-1.5">
											<span class="text-ink-gray-5">{{
												__("Available")
											}}</span>
											<div class="text-ink-gray-8 font-medium">
												{{ couponData.remaining_tickets }}
											</div>
										</div>
									</div>

									<!-- Eligibility indicator -->
									<div
										class="flex items-center justify-between bg-green-50 rounded px-2 py-1.5"
									>
										<span class="text-green-700 text-xs">{{
											__("Eligible attendees")
										}}</span>
										<span class="text-green-700 text-sm-semibold">
											{{ matchingAttendeesCount }}/{{ attendees.length }}
										</span>
									</div>

									<!-- Free add-ons -->
									<div
										v-if="couponData.free_add_ons?.length"
										class="flex items-center gap-1.5 text-xs text-ink-gray-6"
									>
										<LucideGift
											class="w-3.5 h-3.5 text-green-500 flex-shrink-0"
										/>
										<span>{{ __("Free:") }}</span>
										<span
											v-for="(addOn, idx) in couponData.free_add_ons"
											:key="addOn"
											class="text-ink-gray-7"
										>
											{{ addOnsMap[addOn]?.title || addOn
											}}{{
												idx < couponData.free_add_ons.length - 1
													? ", "
													: ""
											}}
										</span>
									</div>
								</div>
							</div>

							<div
								v-if="couponError"
								class="mt-2 flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg"
							>
								<LucideAlertCircle
									class="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5"
								/>
								<span class="text-sm text-amber-800">{{ couponError }}</span>
							</div>
						</div>

						<BookingSummary
							class="mb-6"
							v-if="!eventDetails.free_webinar"
							:summary="summary"
							:net-amount="netAmount"
							:discount-amount="discountAmount"
							:coupon-applied="couponApplied"
							:coupon-type="couponData?.coupon_type || ''"
							:free-add-on-counts="freeAddOnCounts"
							:free-ticket-type="
								couponData?.coupon_type === 'Free Tickets'
									? couponData?.ticket_type
									: ''
							"
							:free-ticket-count="couponData?.remaining_tickets || 0"
							:tax-amount="taxAmount"
							:tax-percentage="taxPercentage"
							:tax-label="taxLabel"
							:tax-inclusive="taxInclusive"
							:should-apply-tax="shouldApplyTax"
							:total="finalTotal"
							:total-currency="totalCurrency"
						/>

						<div class="w-full">
							<Button
								variant="solid"
								size="lg"
								class="w-full"
								type="submit"
								:loading="processBooking.loading || sendOtpResource.loading"
							>
								{{ submitButtonText }}
							</Button>
						</div>
					</div>
				</div>
			</div>
		</form>
	</div>
</template>

<script setup lang="ts">
import { useBookingFormStorage } from "@/composables/useBookingFormStorage";
import { useLoginDialog } from "@/composables/useLoginDialog";
import { userResource } from "@/data/user";
import {
	type BookingSubmitResponse,
	resolveBookingSuccessAction,
} from "@/utils/bookingSuccessRedirect";
import { formatCurrency, formatPriceOrFree } from "@/utils/currency";
import { clearBookingCache } from "@/utils/index";
import BillingDetails from "@/components/BillingDetails.vue";
import type {
	AvailableAddOn,
	AvailableTicketType,
	BookingAttendee,
	CouponData,
	FrappeError,
	FrappeField,
	OfflineMethod,
} from "@/types";
import { FormControl, createResource, toast } from "frappe-ui";
import { type PropType, computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useRouteQuery } from "@vueuse/router";
import LucideAlertCircle from "~icons/lucide/alert-circle";
import LucideCheck from "~icons/lucide/check";
import LucideCheckCircle from "~icons/lucide/check-circle";
import LucideGift from "~icons/lucide/gift";
import LucideX from "~icons/lucide/x";
import AttendeeFormControl from "./AttendeeFormControl.vue";
import BookingSummary from "./BookingSummary.vue";
import CustomFieldsSection from "./CustomFieldsSection.vue";
import EventDetailsHeader from "./EventDetailsHeader.vue";
import OfflinePaymentDialog from "./OfflinePaymentDialog.vue";
import PaymentGatewayDialog from "./PaymentGatewayDialog.vue";

const router = useRouter();
const route = useRoute();
const { open: openLoginDialog } = useLoginDialog();

const getUtmParameters = () => {
	const utmParams: { utm_name: string; value: string }[] = [];
	for (const [key, value] of Object.entries(route.query)) {
		if (key.toLowerCase().startsWith("utm_") && value) {
			utmParams.push({
				utm_name: key,
				value: String(value),
			});
		}
	}
	return utmParams;
};

const props = defineProps({
	availableAddOns: {
		type: Array as PropType<AvailableAddOn[]>,
		default: () => [],
	},
	availableTicketTypes: {
		type: Array as PropType<AvailableTicketType[]>,
		default: () => [],
	},
	taxSettings: {
		type: Object as PropType<Record<string, any>>,
		default: () => ({
			apply_tax: false,
			tax_inclusive: false,
			tax_label: "Tax",
			tax_percentage: 0,
		}),
	},
	eventDetails: {
		type: Object as PropType<Record<string, any>>,
		default: () => ({}),
	},
	customFields: {
		type: Array as PropType<FrappeField[]>,
		default: () => [],
	},
	eventRoute: {
		type: String,
		required: true,
	},
	paymentGateways: {
		type: Array as PropType<any[]>,
		default: () => [],
	},
	isGuestMode: {
		type: Boolean,
		default: false,
	},
	offlineMethods: {
		type: Array as PropType<OfflineMethod[]>,
		default: () => [],
	},
});

// --- STATE ---
// Use the booking form storage composable with event-scoped keys
const {
	attendees,
	attendeeIdCounter,
	bookingCustomFields: storedBookingCustomFields,
	guestFirstName,
	guestLastName,
	guestEmail,
	guestPhone,
	invoiceRequested,
	taxId,
	billingAddress,
} = useBookingFormStorage(props.eventRoute);

const guestFullName = computed(() => `${guestFirstName.value} ${guestLastName.value}`.trim());

// Use stored booking custom fields data
const bookingCustomFieldsData = storedBookingCustomFields;

// Payment gateway dialog state
const showGatewayDialog = ref(false);
const showOfflineDialog = ref(false);
const pendingPayload = ref<any>(null);
const selectedGateway = ref<any>(null);

const isOfflineGateway = (gateway: string) =>
	props.offlineMethods.some((m) => m.title === gateway);

const selectedOfflineMethod = ref<OfflineMethod | null>(null);

const activeOfflineSettings = computed(() => {
	if (!selectedOfflineMethod.value) return {};
	return {
		label: selectedOfflineMethod.value.title,
		payment_details: selectedOfflineMethod.value.description,
		collect_payment_proof: selectedOfflineMethod.value.collect_payment_proof,
	};
});

const activeOfflineCustomFields = computed(() => {
	if (!selectedOfflineMethod.value) return [];
	return selectedOfflineMethod.value.custom_fields || [];
});

// Coupon state — `appliedCouponQuery` keeps the URL in sync with the applied coupon
const appliedCouponQuery = useRouteQuery<string | null>("coupon", null);
const couponCode = ref("");
const couponApplied = ref(false);
const couponError = ref("");
const couponData = ref<CouponData | null>(null);

// Success state for guest bookings
const bookingSuccess = ref(false);
const successBookingName = ref("");

// OTP verification state for guest bookings
const showOtpModal = ref(false);
const otpCode = ref("");
const otpError = ref("");
const pendingBookingPayload = ref<any>(null);
const resendCooldown = ref(0);
let resendCooldownTimer: ReturnType<typeof setInterval> | undefined;

onUnmounted(() => {
	clearInterval(resendCooldownTimer);
});

// Ensure user data is loaded (only if not in guest mode)
if (!props.isGuestMode && !userResource.data) {
	userResource.fetch();
}

// --- HELPERS / DERIVED STATE ---
const addOnsMap = computed(() =>
	Object.fromEntries(props.availableAddOns.map((a) => [a.name, a]))
);
const ticketTypesMap = computed(() =>
	Object.fromEntries(props.availableTicketTypes.map((t) => [t.name, t]))
);
const eventId = computed(() => props.availableTicketTypes[0]?.event || null);

// Separate custom fields by applied_to
const bookingCustomFields = computed(() =>
	props.customFields.filter((field) => field.applied_to === "Booking")
);

const ticketCustomFields = computed(() =>
	props.customFields.filter((field) => field.applied_to === "Ticket")
);

const getDefaultTicketType = () => {
	// Use the default ticket type from event details if set
	const defaultTicketType = props.eventDetails?.default_ticket_type;
	if (defaultTicketType) {
		// Verify that the default ticket type is available
		const isAvailable = props.availableTicketTypes.some((tt) => tt.name == defaultTicketType);
		if (isAvailable) {
			return String(defaultTicketType);
		}
	}
	// Fall back to the first available ticket type
	return String(props.availableTicketTypes[0]?.name || "");
};

const createNewAttendee = (): BookingAttendee => {
	attendeeIdCounter.value++;
	const newAttendee: BookingAttendee = {
		id: attendeeIdCounter.value,
		first_name: "",
		last_name: "",
		email: "",
		// Use default ticket type from event details, or first available
		ticket_type: getDefaultTicketType(),
		add_ons: {},
		custom_fields: {},
	};
	for (const addOn of props.availableAddOns) {
		newAttendee.add_ons![addOn.name] = {
			selected: false,
			option: addOn.options ? addOn.options[0] || null : null,
		};
	}

	// Initialize custom fields with default values
	for (const field of ticketCustomFields.value) {
		if (field.default_value) {
			newAttendee.custom_fields![field.fieldname] = field.default_value;
		}
	}

	return newAttendee;
};

const addAttendee = () => {
	const newAttendee = createNewAttendee();
	attendees.value.push(newAttendee);
};

const removeAttendee = (index: number) => {
	attendees.value.splice(index, 1);
};

// --- COMPUTED PROPERTIES FOR SUMMARY ---
interface SummaryLine {
	count: number;
	amount: number;
	price?: number;
	title?: string;
	currency?: string;
}

const summary = computed(() => {
	const summaryData: {
		tickets: Record<string, SummaryLine>;
		add_ons: Record<string, SummaryLine>;
	} = { tickets: {}, add_ons: {} };

	for (const attendee of attendees.value) {
		const ticketType = attendee.ticket_type;
		if (ticketType && ticketTypesMap.value[ticketType]) {
			const ticketInfo = ticketTypesMap.value[ticketType];
			if (!summaryData.tickets[ticketType]) {
				summaryData.tickets[ticketType] = {
					count: 0,
					amount: 0,
					price: ticketInfo.price,
					title: ticketInfo.title,
					currency: ticketInfo.currency,
				};
			}
			summaryData.tickets[ticketType].count++;
			summaryData.tickets[ticketType].amount += ticketInfo.price ?? 0;
		}

		for (const addOnName in attendee.add_ons) {
			if (attendee.add_ons[addOnName].selected) {
				const addOnInfo = addOnsMap.value[addOnName];
				// Skip if add-on no longer exists (e.g., was disabled)
				if (!addOnInfo) continue;

				if (!summaryData.add_ons[addOnName]) {
					summaryData.add_ons[addOnName] = {
						count: 0,
						amount: 0,
						price: addOnInfo.price,
						title: addOnInfo.title,
						currency: addOnInfo.currency,
					};
				}
				summaryData.add_ons[addOnName].count++;
				summaryData.add_ons[addOnName].amount += addOnInfo.price ?? 0;
			}
		}
	}
	return summaryData;
});

const total = computed(() => {
	let currentTotal = 0;
	for (const key in summary.value.tickets) {
		currentTotal += summary.value.tickets[key].amount;
	}
	for (const key in summary.value.add_ons) {
		currentTotal += summary.value.add_ons[key].amount;
	}
	return currentTotal;
});

// Net amount (before tax)
const netAmount = computed(() => total.value);

// Tax calculations
const shouldApplyTax = computed(() => {
	return props.taxSettings?.apply_tax;
});

const taxLabel = computed(() => {
	return props.taxSettings?.tax_label || "Tax";
});

const taxPercentage = computed(() => {
	return shouldApplyTax.value ? props.taxSettings?.tax_percentage || 0 : 0;
});

// Count of attendees matching the coupon's ticket type (for Free Tickets)
const matchingAttendeesCount = computed(() => {
	const coupon = couponData.value;
	if (!coupon || coupon.coupon_type !== "Free Tickets") return 0;
	return attendees.value.filter((a) => String(a.ticket_type) === String(coupon.ticket_type))
		.length;
});

// Discount amount based on coupon
const discountAmount = computed(() => {
	if (!couponApplied.value || !couponData.value) return 0;

	// Free Tickets - only discount attendees with matching ticket type
	if (couponData.value.coupon_type === "Free Tickets") {
		const couponTicketType = couponData.value.ticket_type ?? "";
		const ticketInfo = ticketTypesMap.value[couponTicketType];
		if (!ticketInfo) return 0;

		// Count only attendees with matching ticket type
		const matchingAttendees = attendees.value.filter(
			(a) => String(a.ticket_type) === String(couponTicketType)
		);
		const freeTicketCount = Math.min(
			matchingAttendees.length,
			couponData.value.remaining_tickets ?? 0
		);
		let discount = freeTicketCount * (ticketInfo.price ?? 0);

		// Add free add-ons discount for free ticket holders only
		if (couponData.value.free_add_ons && couponData.value.free_add_ons.length > 0) {
			for (let i = 0; i < freeTicketCount; i++) {
				const attendee = matchingAttendees[i];
				if (attendee) {
					for (const freeAddOnName of couponData.value.free_add_ons) {
						if (attendee.add_ons?.[freeAddOnName]?.selected) {
							const addOnInfo = addOnsMap.value[freeAddOnName];
							if (addOnInfo) {
								discount += addOnInfo.price ?? 0;
							}
						}
					}
				}
			}
		}

		return discount;
	}

	// Discount coupon
	if (couponData.value.discount_type === "Percentage") {
		let discount = netAmount.value * ((couponData.value.discount_value ?? 0) / 100);
		if ((couponData.value.max_discount_amount ?? 0) > 0) {
			discount = Math.min(discount, couponData.value.max_discount_amount ?? 0);
		}
		return discount;
	}
	return Math.min(couponData.value.discount_value ?? 0, netAmount.value);
});

// Calculate free add-on counts for display
const freeAddOnCounts = computed(() => {
	if (!couponApplied.value || couponData.value?.coupon_type !== "Free Tickets") return {};
	if (!couponData.value.free_add_ons?.length) return {};

	const counts: Record<string, number> = {};
	const couponTicketType = couponData.value.ticket_type;
	const matchingAttendees = attendees.value.filter(
		(a) => String(a.ticket_type) === String(couponTicketType)
	);
	const freeTicketCount = Math.min(
		matchingAttendees.length,
		couponData.value.remaining_tickets ?? 0
	);

	for (const addOnName of couponData.value.free_add_ons) {
		let count = 0;
		for (let i = 0; i < freeTicketCount; i++) {
			if (matchingAttendees[i]?.add_ons?.[addOnName]?.selected) count++;
		}
		if (count > 0) counts[addOnName] = count;
	}
	return counts;
});

// Amount after discount
const amountAfterDiscount = computed(() => {
	return netAmount.value - discountAmount.value;
});

const taxInclusive = computed(() => {
	return props.taxSettings?.tax_inclusive;
});

const taxAmount = computed(() => {
	if (!shouldApplyTax.value) return 0;
	if (taxInclusive.value) {
		// Tax is included in the price — back-calculate the tax component
		return (
			Math.round(
				((amountAfterDiscount.value * taxPercentage.value) / (100 + taxPercentage.value)) *
					100
			) / 100
		);
	}
	return (amountAfterDiscount.value * taxPercentage.value) / 100;
});

const finalTotal = computed(() => {
	if (taxInclusive.value) {
		// Price already includes tax — total stays the same
		return amountAfterDiscount.value;
	}
	return amountAfterDiscount.value + taxAmount.value;
});

// Determine the primary currency for the total (use the first ticket type's currency)
const totalCurrency = computed(() => {
	const firstTicket = Object.values(summary.value.tickets)[0];
	return firstTicket ? firstTicket.currency : "INR";
});

// Initialize with one attendee when component mounts (only if no data in storage)
onMounted(async () => {
	await nextTick();
	if (attendees.value.length === 0 && props.availableTicketTypes.length > 0) {
		const newAttendee = createNewAttendee();

		if (guestFirstName.value || guestEmail.value) {
			newAttendee.first_name = guestFirstName.value;
			newAttendee.last_name = guestLastName.value;
			newAttendee.email = guestEmail.value;
		} else if (userResource.data) {
			newAttendee.first_name = userResource.data.first_name || "";
			newAttendee.last_name = userResource.data.last_name || "";
			newAttendee.email = userResource.data.email || "";
		}

		attendees.value = [newAttendee];
	}

	// Pre-fill and auto-apply coupon from ?coupon= query param
	const initialCoupon = appliedCouponQuery.value;
	if (typeof initialCoupon === "string" && initialCoupon.trim() && !couponApplied.value) {
		couponCode.value = initialCoupon.trim().toUpperCase();
		await applyCoupon();
	}
});

// Ensure existing attendees have proper add-on structure when availableAddOns changes
watch(
	() => props.availableAddOns,
	(newAddOns) => {
		if (newAddOns && newAddOns.length > 0) {
			for (const attendee of attendees.value) {
				if (!attendee.add_ons) {
					attendee.add_ons = {};
				}
				// Ensure all available add-ons are represented in the attendee's add_ons
				for (const addOn of newAddOns) {
					if (!attendee.add_ons[addOn.name]) {
						attendee.add_ons[addOn.name] = {
							selected: false,
							option: addOn.options ? addOn.options[0] || null : null,
						};
					}
				}
			}
		}
	},
	{ immediate: true, deep: true }
);

// Auto-select ticket type based on event's default or if there's only one available
// Also revalidate stored ticket types (from localStorage) against currently available ones
watch(
	() => props.availableTicketTypes,
	(newTicketTypes) => {
		if (newTicketTypes && newTicketTypes.length > 0) {
			const defaultTicketType = getDefaultTicketType();
			const availableIds = new Set(newTicketTypes.map((tt) => String(tt.name)));
			for (const attendee of attendees.value) {
				if (
					!attendee.ticket_type ||
					attendee.ticket_type === "" ||
					!availableIds.has(String(attendee.ticket_type))
				) {
					attendee.ticket_type = defaultTicketType;
				}
			}
		}
	},
	{ immediate: true }
);

// Initialize booking custom fields with default values
watch(
	() => bookingCustomFields.value,
	(fields) => {
		if (fields && fields.length > 0) {
			for (const field of fields) {
				// Only set default value if field doesn't already have a value
				if (field.default_value && !bookingCustomFieldsData.value[field.fieldname]) {
					bookingCustomFieldsData.value[field.fieldname] = field.default_value;
				}
			}
		}
	},
	{ immediate: true }
);

watch(netAmount, (newVal) => {
	if (couponApplied.value && (couponData.value?.min_order_value ?? 0) > 0) {
		if (newVal < (couponData.value?.min_order_value ?? 0)) {
			removeCoupon();
			toast.warning(__("Coupon removed - minimum order not met"));
		}
	}
});

watch(matchingAttendeesCount, (newCount) => {
	if (
		newCount === 0 &&
		couponApplied.value &&
		couponData.value?.coupon_type === "Free Tickets"
	) {
		removeCoupon();
		toast.warning(__("Coupon removed — no eligible attendees for this ticket type"));
	}
});

function prefillAttendee(field: string) {
	if (!props.isGuestMode || !attendees.value.length) return;
	const first = attendees.value[0];
	if (field === "name") {
		if (!first.first_name) first.first_name = guestFirstName.value;
		if (!first.last_name) first.last_name = guestLastName.value;
	}
	if (field === "email" && !first.email) first.email = guestEmail.value;
}

const processBooking = createResource({
	url: "buzz.api.process_booking",
});

const validateCoupon = createResource({
	url: "buzz.api.validate_coupon",
});

function startResendCooldown() {
	resendCooldown.value = 30;
	clearInterval(resendCooldownTimer);
	resendCooldownTimer = setInterval(() => {
		resendCooldown.value--;
		if (resendCooldown.value <= 0) {
			clearInterval(resendCooldownTimer);
		}
	}, 1000);
}

const sendOtpResource = createResource({
	url: "buzz.api.send_guest_booking_otp",
	onSuccess: () => {
		showOtpModal.value = true;
		startResendCooldown();
		toast.success(
			isPhoneOtp.value
				? __("Verification code sent to your phone")
				: __("Verification code sent to your email")
		);
	},
	onError: (error: FrappeError) => {
		toast.error(error.messages?.[0] || __("Failed to send verification code"));
	},
});

const isPhoneOtp = computed(() => props.eventDetails.guest_verification_method === "Phone OTP");

function sendOtpForVerification() {
	sendOtpResource.submit({
		event: props.eventDetails.name,
		identifier: isPhoneOtp.value ? guestPhone.value.trim() : guestEmail.value.trim(),
	});
}

// --- COUPON FUNCTIONS ---
async function applyCoupon() {
	const normalizedCode = couponCode.value.trim().toUpperCase();
	if (!normalizedCode) {
		couponError.value = __("Please enter a coupon code");
		return;
	}

	// Reflect normalized casing back into the input / applied card
	couponCode.value = normalizedCode;

	couponError.value = "";
	let result;
	try {
		const params: Record<string, any> = {
			coupon_code: normalizedCode,
			event: eventId.value,
		};
		// Pass user email for guest mode to properly check per-user limits
		if (props.isGuestMode && guestEmail.value.trim()) {
			params.user_email = guestEmail.value.trim().toLowerCase();
		}
		result = await validateCoupon.submit(params);
	} catch (error) {
		couponError.value = (error as FrappeError).message || __("Failed to validate coupon");
		return;
	}

	if (result.valid) {
		if (
			result.coupon_type === "Discount" &&
			result.min_order_value > 0 &&
			netAmount.value < result.min_order_value
		) {
			const gap = result.min_order_value - netAmount.value;
			couponError.value = __("Add {0} more to use this coupon (min order {1})", [
				formatCurrency(gap, totalCurrency.value),
				formatCurrency(result.min_order_value, totalCurrency.value),
			]);
			return;
		}

		couponApplied.value = true;

		if (result.coupon_type === "Discount") {
			couponData.value = {
				coupon_type: "Discount",
				discount_type: result.discount_type,
				discount_value: result.discount_value,
				max_discount_amount: result.max_discount_amount || 0,
				min_order_value: result.min_order_value || 0,
			};
			toast.success(__("Coupon applied successfully!"));
		} else if (result.coupon_type === "Free Tickets") {
			couponData.value = {
				coupon_type: "Free Tickets",
				ticket_type: String(result.ticket_type),
				remaining_tickets: result.remaining_tickets,
				free_add_ons: result.free_add_ons || [],
			};
			// Info panel shows details - no toast needed
		}

		appliedCouponQuery.value = normalizedCode;
	} else {
		couponApplied.value = false;
		couponData.value = null;
		couponError.value = result.error;
	}
}

function removeCoupon() {
	couponCode.value = "";
	couponApplied.value = false;
	couponData.value = null;
	couponError.value = "";
	appliedCouponQuery.value = null;
}

// --- FORM VALIDATION ---
const validateForm = () => {
	const errors = [];

	// Validate booking-level mandatory fields
	for (const field of bookingCustomFields.value) {
		if (field.mandatory) {
			const value = bookingCustomFieldsData.value[field.fieldname];
			if (!value || !String(value).trim()) {
				errors.push(`${field.label} is required`);
			}
		}
	}

	// Validate last name is provided for webinar events
	if (isWebinar.value) {
		attendees.value.forEach((attendee, index) => {
			if (!attendee.last_name?.trim()) {
				errors.push(__("Last Name is required for Attendee #{0}", [index + 1]));
			}
		});
	}

	// Validate ticket-level mandatory fields for each attendee
	attendees.value.forEach((attendee, index) => {
		for (const field of ticketCustomFields.value) {
			if (field.mandatory) {
				const value = attendee.custom_fields?.[field.fieldname];
				if (!value || !String(value).trim()) {
					errors.push(`${field.label} is required for Attendee #${index + 1}`);
				}
			}
		}
	});

	return errors;
};

// --- FORM SUBMISSION ---
async function submit() {
	if (processBooking.loading) return;

	if (requiresLogin.value) {
		openLoginDialog();
		return;
	}

	// Validate mandatory fields
	const validationErrors = validateForm();
	if (validationErrors.length > 0) {
		// Show the first error as toast, or all errors if only a few
		if (validationErrors.length === 1) {
			toast.error(validationErrors[0]);
		} else if (validationErrors.length <= 3) {
			toast.error(`Please fill in the required fields:\n${validationErrors.join("\n")}`);
		} else {
			toast.error(`Please fill in ${validationErrors.length} required fields.`);
		}
		return;
	}

	const attendees_payload = attendees.value.map((attendee) => {
		const cleanAttendee = JSON.parse(JSON.stringify(attendee));
		const selected_add_ons = [];
		for (const addOnName in cleanAttendee.add_ons) {
			const addOnState = cleanAttendee.add_ons[addOnName];
			if (addOnState.selected) {
				selected_add_ons.push({
					add_on: addOnName,
					value: addOnState.option || true,
				});
			}
		}
		cleanAttendee.add_ons = selected_add_ons;

		// Clean custom fields - include all valid fields (mandatory fields are validated separately)
		if (cleanAttendee.custom_fields) {
			const cleanedCustomFields: Record<string, any> = {};
			for (const [fieldName, value] of Object.entries(cleanAttendee.custom_fields)) {
				// Check if this is a valid custom field for tickets
				const fieldDef = ticketCustomFields.value.find((cf) => cf.fieldname === fieldName);
				if (fieldDef) {
					// Include mandatory fields even if empty (validation already passed)
					// For non-mandatory fields, only include if they have values
					if (fieldDef.mandatory || (value != null && String(value).trim())) {
						cleanedCustomFields[fieldName] = value || "";
					}
				}
			}
			cleanAttendee.custom_fields =
				Object.keys(cleanedCustomFields).length > 0 ? cleanedCustomFields : null;
		}

		return cleanAttendee;
	});

	// Clean booking custom fields
	const cleanedBookingCustomFields: Record<string, any> = {};
	for (const [fieldName, value] of Object.entries(bookingCustomFieldsData.value)) {
		// Check if this is a valid custom field for bookings
		const fieldDef = bookingCustomFields.value.find((cf) => cf.fieldname === fieldName);
		if (fieldDef) {
			// Include mandatory fields even if empty (validation already passed)
			// For non-mandatory fields, only include if they have values
			if (fieldDef.mandatory || (value != null && String(value).trim())) {
				cleanedBookingCustomFields[fieldName] = value || "";
			}
		}
	}

	const utmParameters = getUtmParameters();

	const final_payload = {
		event: eventId.value,
		attendees: attendees_payload,
		coupon_code: couponApplied.value ? couponCode.value.trim() : null,
		booking_custom_fields:
			Object.keys(cleanedBookingCustomFields).length > 0 ? cleanedBookingCustomFields : null,
		utm_parameters: utmParameters.length > 0 ? utmParameters : null,
		guest_email: props.isGuestMode ? guestEmail.value.trim() : null,
		guest_full_name: props.isGuestMode ? guestFullName.value.trim() : null,
		guest_phone: props.isGuestMode && isPhoneOtp.value ? guestPhone.value.trim() : null,
		invoice_requested: invoiceRequested.value,
		tax_id: invoiceRequested.value ? taxId.value?.trim() : null,
		billing_address: invoiceRequested.value ? billingAddress.value?.trim() : null,
	};

	if (props.isGuestMode) {
		if (!guestFirstName.value.trim()) {
			toast.error(__("Please enter your first name"));
			return;
		}
		if (isWebinar.value && !guestLastName.value.trim()) {
			toast.error(__("Please enter your last name"));
			return;
		}
		if (!guestEmail.value.trim()) {
			toast.error(__("Please enter your email address"));
			return;
		}
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		if (!emailRegex.test(guestEmail.value.trim())) {
			toast.error(__("Please enter a valid email address"));
			return;
		}
		if (isPhoneOtp.value && !guestPhone.value.trim()) {
			toast.error(__("Please enter your phone number"));
			return;
		}
		pendingBookingPayload.value = final_payload;

		// OTP verification must happen before payment gateway selection
		if (props.eventDetails.guest_verification_method !== "None") {
			sendOtpForVerification();
			return;
		}

		// No OTP required - proceed with payment gateway selection
		if (finalTotal.value > 0) {
			if (props.paymentGateways.length > 1) {
				pendingPayload.value = final_payload;
				showGatewayDialog.value = true;
				return;
			} else if (props.paymentGateways.length === 1) {
				const singleGateway = props.paymentGateways[0];
				if (isOfflineGateway(singleGateway)) {
					pendingPayload.value = final_payload;
					selectedOfflineMethod.value =
						props.offlineMethods.find((m) => m.title === singleGateway) || null;
					showOfflineDialog.value = true;
					return;
				}
			}
		}

		selectedGateway.value = props.paymentGateways[0] || null;
		submitBooking(final_payload, selectedGateway.value);
		return;
	}

	if (finalTotal.value > 0) {
		if (props.paymentGateways.length > 1) {
			pendingPayload.value = final_payload;
			showGatewayDialog.value = true;
			return;
		} else if (props.paymentGateways.length === 1) {
			const singleGateway = props.paymentGateways[0];
			if (isOfflineGateway(singleGateway)) {
				pendingPayload.value = final_payload;
				selectedOfflineMethod.value =
					props.offlineMethods.find((m) => m.title === singleGateway) || null;
				showOfflineDialog.value = true;
				return;
			}
		}
	}

	submitBooking(final_payload, props.paymentGateways[0] || null);
}

function submitBooking(
	payload: any,
	paymentGateway: any,
	{ isOtpFlow = false }: { isOtpFlow?: boolean } = {}
) {
	processBooking.submit(
		{
			...payload,
			payment_gateway: paymentGateway,
		},
		{
			onSuccess: (data: BookingSubmitResponse) => {
				clearBookingCache();

				if (isOtpFlow) {
					clearOtpState();
				}

				const action = resolveBookingSuccessAction(data, {
					isGuestMode: props.isGuestMode,
				});

				if (action.type === "external") {
					window.location.href = action.url;
				} else if (action.type === "guest-inline") {
					bookingSuccess.value = true;
					successBookingName.value = action.bookingName;
				} else {
					router.replace(action.path);
				}
			},
			onError: (error: FrappeError) => {
				const message = error.messages?.[0] || error.message || __("Booking failed");

				if (isOtpFlow) {
					otpCode.value = "";
					// Close modal on lockout or expired OTP - user must restart
					if (message.includes("Too many") || message.includes("expired")) {
						showOtpModal.value = false;
						toast.error(message);
					} else {
						otpError.value = message;
					}
				} else {
					toast.error(message);
				}
			},
		}
	);
}

function onOfflinePaymentSubmit(data: any) {
	if (pendingPayload.value) {
		const payloadWithProof = {
			...pendingPayload.value,
			payment_proof: data?.payment_proof?.file_url || null,
			is_offline: true,
			offline_payment_method: selectedOfflineMethod.value?.name
				? String(selectedOfflineMethod.value.name)
				: null,
		};
		submitBooking(payloadWithProof, null);
		pendingPayload.value = null;
		showOfflineDialog.value = false;
	}
}

function onGatewaySelected(gateway: string) {
	showGatewayDialog.value = false;
	selectedGateway.value = gateway;

	if (pendingPayload.value) {
		if (isOfflineGateway(gateway)) {
			selectedOfflineMethod.value =
				props.offlineMethods.find((m) => m.title === gateway) || null;
			showOfflineDialog.value = true;
		} else {
			submitBooking(pendingPayload.value, gateway);
			pendingPayload.value = null;
		}
	}
}

function submitWithOtp() {
	if (!otpCode.value.trim()) {
		otpError.value = __("Please enter the verification code");
		return;
	}

	const payloadWithOtp = {
		...pendingBookingPayload.value,
		otp: otpCode.value.trim(),
	};

	// After OTP verification, check payment gateway selection
	if (finalTotal.value > 0) {
		if (props.paymentGateways.length > 1) {
			pendingPayload.value = payloadWithOtp;
			showOtpModal.value = false;
			showGatewayDialog.value = true;
			return;
		} else if (props.paymentGateways.length === 1) {
			const singleGateway = props.paymentGateways[0];
			if (isOfflineGateway(singleGateway)) {
				pendingPayload.value = payloadWithOtp;
				selectedOfflineMethod.value =
					props.offlineMethods.find((m) => m.title === singleGateway) || null;
				showOtpModal.value = false;
				showOfflineDialog.value = true;
				return;
			}
			selectedGateway.value = singleGateway;
		}
	}

	submitBooking(payloadWithOtp, selectedGateway.value || null, {
		isOtpFlow: true,
	});
}

function resendOtp() {
	if (sendOtpResource.loading || resendCooldown.value > 0) return;
	otpCode.value = "";
	sendOtpForVerification();
}

function clearOtpState() {
	showOtpModal.value = false;
	otpCode.value = "";
	otpError.value = "";
	pendingBookingPayload.value = null;
	selectedGateway.value = null;
	resendCooldown.value = 0;
	clearInterval(resendCooldownTimer);
}

const isWebinar = computed(() => props.eventDetails.category === "Webinars");

const requiresLogin = computed(() => {
	return props.isGuestMode && !props.eventDetails?.allow_guest_booking;
});

const submitButtonText = computed(() => {
	if (processBooking.loading) {
		return __("Processing...");
	}

	if (requiresLogin.value) {
		return __("Book Tickets");
	}

	if (finalTotal.value > 0) {
		return __("Pay & Book");
	}

	if (isWebinar.value) {
		return __("Register");
	}

	return __("Book Tickets");
});
</script>
