<template>
	<div>
		<OtpDialog
			v-model:open="otp.open"
			v-model:code="otp.code"
			:is-phone="isPhoneOtp"
			:identifier="isPhoneOtp ? billing.buyer_phone : billing.buyer_email"
			:error="otp.error"
			:resend-cooldown="otp.cooldown"
			:resending="otp.sending"
			:verifying="placing"
			@resend="otp.resend"
			@verify="verifyOtp"
			@cancel="otp.reset"
			@clear-error="otp.error = ''"
		/>
		<OfflinePaymentDialog
			v-model:open="showOfflineDialog"
			:amount="total"
			:currency="currency"
			:offline-settings="activeOfflineSettings"
			:loading="placing"
			:custom-fields="activeOfflineCustomFields"
			@submit="submitOffline"
			@cancel="showOfflineDialog = false"
		/>

		<RegistrationComplete
			v-if="completed"
			:title="successTitle"
			:reference="completed.pendingVerification ? completed.bookingName : undefined"
			:pending="completed.pendingVerification"
			@login="openLoginDialog()"
		>
			{{ successMessage }}
		</RegistrationComplete>

		<template v-else>
			<CheckoutHeader
				v-if="!isMobile"
				:event-details="eventDetails"
				:event-route="eventRoute"
				:seconds-left="expired ? null : secondsLeft"
			/>
			<MobileStepBar
				v-else
				:title="__(eventDetails.title)"
				:steps="steps"
				:current="current"
				@back="back"
			/>

			<form
				class="mx-auto grid max-w-6xl items-start gap-10 px-4 pb-48 pt-5 md:px-6 lg:grid-cols-[190px_minmax(0,1fr)_320px] lg:pb-16 lg:pt-7"
				:class="{ 'max-w-xl': isMobile }"
				novalidate
				@submit.prevent="next"
			>
				<RegistrationStepRail
					v-if="!isMobile"
					class="sticky top-20"
					:steps="steps"
					:current="current"
					@go="go"
				/>

				<Transition :name="isMobile ? 'step-slide' : 'step-rise'" mode="out-in">
					<section
						:key="step.id"
						class="flex min-w-0 flex-col gap-6"
						:style="{ '--direction': direction }"
					>
						<header class="flex flex-col gap-1.5">
							<h1 class="text-xl-semibold tracking-[-0.01em] text-ink-gray-9 md:text-2xl-semibold">
								{{ stepCopy.title }}
							</h1>
							<p class="text-base text-ink-gray-6 text-pretty">{{ stepCopy.description }}</p>
						</header>

						<div v-if="step.id === 'tickets'" class="flex flex-col gap-7">
							<CurrencySwitch
								v-if="currencies.length > 1 && !eventDetails.free_event"
								:currencies="currencies"
								:model-value="currency"
								:removed-message="removedMessage"
								@update:model-value="setCurrency"
								@undo="undoCurrency"
							/>
							<TicketTierPicker
								:ticket-types="ticketTypes"
								:categories="ticketCategories"
								:quantities="quantities"
								:currency="currency"
								:stepper-size="isMobile ? 'lg' : 'sm'"
								@change="changeQuantity"
							/>
						</div>

						<AttendeesStep
							v-else-if="step.id === 'attendees'"
							:attendees="attendees"
							:me="me"
							:me-errors="meErrors"
							:errors="attendeeErrorList"
							:ticket-types="ticketTypes"
							:categories="ticketCategories"
							:add-ons="addOns"
							:custom-fields="ticketCustomFields"
							:fields-for="ticketFieldsFor"
							:show-errors="tried"
							:last-name-required="isZoomEvent"
							:collapsible="isMobile"
						/>

						<DetailsStep
							v-else-if="step.id === 'details'"
							v-model:booking-custom-fields-data="bookingCustomFieldsData"
							:billing="billing"
							:phone-required="isGuestMode && isPhoneOtp"
							:phone-error="otp.phoneError"
							:booking-custom-fields="bookingCustomFields"
							:show-invoice="tax.apply"
							:tax-label="tax.label"
							:errors="detailsErrors"
							:show-errors="tried"
							:large="isMobile"
						/>

						<SummaryStep
							v-else
							:event-details="eventDetails"
							:attendees="attendees"
							:me="me"
							:ticket-types-map="ticketTypesMap"
							:add-ons-map="addOnsMap"
							:billing="billing"
							:invoice-shown="tax.apply"
							:tax-label="tax.label"
							:currency="currency"
							:show-currency="currencies.length > 1"
							@edit="goToStep"
						>
							<template #totals>
								<OrderSummary v-bind="summaryProps" :lines="undefined" />
							</template>
							<PaymentStep
								v-model="selectedGateway"
								:gateways="gateways"
								:offline-gateways="offlineGatewayTitles"
							/>
						</SummaryStep>

						<p v-if="isMobile && showStepError" class="text-center text-p-sm text-ink-red-6">
							{{ stepErrorMessage }}
						</p>
					</section>
				</Transition>

				<aside v-if="!isMobile" class="sticky top-20 flex flex-col gap-3">
					<div class="overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-gray-1">
						<div class="flex items-center justify-between gap-2 px-4 pb-3 pt-4">
							<h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Order summary") }}</h2>
							<Badge v-if="currencies.length > 1" :label="currency" />
						</div>
						<OrderSummary v-bind="summaryProps">
							<template v-if="showCoupon" #coupon>
								<CouponField
									v-bind="couponProps"
									v-model="coupon.code"
									@apply="coupon.apply"
									@remove="coupon.remove"
								/>
							</template>
						</OrderSummary>
					</div>
					<TicketHoldTimer
						v-if="expired"
						:seconds-left="secondsLeft"
						:expired="expired"
						@hold-again="holdAgain"
					/>
					<ErrorMessage :message="holdErrorMessage" />
					<Button
						variant="solid"
						size="lg"
						type="submit"
						class="w-full"
						:loading="submitting"
						:disabled="!attendees.length"
					>
						{{ ctaLabel }}
					</Button>
					<p v-if="showStepError" class="text-center text-p-sm text-ink-red-6">
						{{ stepErrorMessage }}
					</p>
					<Button
						v-if="current > 0"
						variant="ghost"
						icon-left="lucide-arrow-left"
						class="w-full"
						@click="back"
					>
						{{ __("Back to {0}", [steps[current - 1].label.toLowerCase()]) }}
					</Button>
				</aside>

				<MobileTotalBar
					v-else
					:count-label="countLabel"
					:total="attendees.length ? formatWholePriceOrFree(total, currency) : '—'"
					:before="
						discountAmount > 0 ? formatWholePriceOrFree(totalBeforeDiscount, currency) : undefined
					"
					@open-summary="showSummarySheet = true"
				>
					<template #notice>
						<TicketHoldTimer
							:seconds-left="secondsLeft"
							:expired="expired"
							@hold-again="holdAgain"
						/>
					</template>
					<Button
						variant="solid"
						size="lg"
						type="submit"
						icon-right="lucide-arrow-right"
						:loading="submitting"
						:disabled="!attendees.length"
					>
						{{ mobileCtaLabel }}
					</Button>
				</MobileTotalBar>
			</form>

			<BottomSheet v-if="isMobile" v-model:open="showSummarySheet" :title="__('Order summary')">
				<div class="pb-6">
					<OrderSummary v-bind="summaryProps">
						<template v-if="showCoupon" #coupon>
							<CouponField
								v-bind="couponProps"
								v-model="coupon.code"
								@apply="coupon.apply"
								@remove="coupon.remove"
							/>
						</template>
					</OrderSummary>
				</div>
			</BottomSheet>
		</template>
	</div>
</template>

<script setup lang="ts">
import { breakpointsTailwind, useBreakpoints } from "@vueuse/core"
import { Badge, BottomSheet, Button, ErrorMessage } from "frappe-ui"
import {
	type PropType,
	computed,
	nextTick,
	onMounted,
	onUnmounted,
	reactive,
	ref,
	watch,
	watchEffect,
} from "vue"
import { useRoute } from "vue-router"

import { useBookingFormStorage } from "@/composables/useBookingFormStorage"
import { useLoginDialog } from "@/composables/useLoginDialog"
import { useTicketHold } from "@/composables/useTicketHold"
import { loadUser, userResource } from "@/data/user"
import type {
	AvailableAddOn,
	AvailableTicketType,
	BookingAttendee,
	BookingTicketCategory,
	FrappeField,
	OfflineMethod,
} from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"
import { eventPath } from "@/utils/eventUrl"
import { applyLogic, type LogicRule } from "@/utils/formLogic"
import { siteHeaderHidden } from "@/utils/navbar"
import { serverErrorMessage } from "@/utils/serverError"
import { isZoomBackedCategory } from "@/utils/zoomCategory"

import OfflinePaymentDialog from "./OfflinePaymentDialog.vue"
import AttendeesStep from "./registration/AttendeesStep.vue"
import CheckoutHeader from "./registration/CheckoutHeader.vue"
import CouponField from "./registration/CouponField.vue"
import CurrencySwitch from "./registration/CurrencySwitch.vue"
import DetailsStep from "./registration/DetailsStep.vue"
import MobileStepBar from "./registration/MobileStepBar.vue"
import MobileTotalBar from "./registration/MobileTotalBar.vue"
import OrderSummary from "./registration/OrderSummary.vue"
import OtpDialog from "./registration/OtpDialog.vue"
import PaymentStep from "./registration/PaymentStep.vue"
import RegistrationComplete from "./registration/RegistrationComplete.vue"
import RegistrationStepRail from "./registration/RegistrationStepRail.vue"
import { buildSteps, isGstLabel, stepCopy as copyFor } from "./registration/registrationSteps"
import SummaryStep from "./registration/SummaryStep.vue"
import TicketTierPicker from "./registration/TicketTierPicker.vue"
import {
	attendeePayload,
	cleanCustomFields,
	useBookingSubmit,
} from "./registration/useBookingSubmit"
import { pricedIn, useCurrencySwitch } from "./registration/useCurrencySwitch"
import { useGuestOtp } from "./registration/useGuestOtp"
import { useOrderPricing } from "./registration/useOrderPricing"
import { type RegistrationStepId, useRegistrationSteps } from "./registration/useRegistrationSteps"
import { useRegistrationValidation } from "./registration/useRegistrationValidation"
import TicketHoldTimer from "./TicketHoldTimer.vue"

const props = defineProps({
	availableAddOns: { type: Array as PropType<AvailableAddOn[]>, default: () => [] },
	availableTicketTypes: { type: Array as PropType<AvailableTicketType[]>, default: () => [] },
	ticketCategories: { type: Array as PropType<BookingTicketCategory[]>, default: () => [] },
	taxSettings: { type: Object as PropType<Record<string, any>>, default: () => ({}) },
	eventDetails: { type: Object as PropType<Record<string, any>>, default: () => ({}) },
	customFields: { type: Array as PropType<FrappeField[]>, default: () => [] },
	// Show, hide and require rules per registration form, keyed like a field's applied_to.
	logicRules: { type: Object as PropType<Record<string, LogicRule[]>>, default: () => ({}) },
	eventRoute: { type: String, required: true },
	paymentGateways: { type: Array as PropType<string[]>, default: () => [] },
	isGuestMode: { type: Boolean, default: false },
	offlineMethods: { type: Array as PropType<OfflineMethod[]>, default: () => [] },
})

const route = useRoute()
const { open: openLoginDialog } = useLoginDialog()
const isMobile = useBreakpoints(breakpointsTailwind).smaller("lg")

const {
	attendees,
	attendeeIdCounter,
	bookingCustomFields: bookingCustomFieldsData,
	guestFirstName,
	guestLastName,
	guestEmail,
	billing,
} = useBookingFormStorage(props.eventRoute)

// The person registering: the guest's contact, or prefilled from the signed-in user.
const me = reactive({
	first_name: guestFirstName,
	last_name: guestLastName,
	email: guestEmail,
})

if (!props.isGuestMode) loadUser()

const isZoomEvent = computed(() => isZoomBackedCategory(props.eventDetails.category))
const isPhoneOtp = computed(() => props.eventDetails.guest_verification_method === "Phone OTP")
const requiresLogin = computed(() => props.isGuestMode && !props.eventDetails?.allow_guest_booking)
const bookingCustomFields = computed(() =>
	applyLogic(
		props.customFields.filter((field) => field.applied_to === "Booking"),
		props.logicRules.Booking || [],
		billing.value,
		bookingCustomFieldsData.value,
	),
)
const ticketCustomFields = computed(() =>
	props.customFields.filter((field) => field.applied_to === "Ticket"),
)
// The attendee questions each ticket asks: rules may name the ticket type or answers above.
function ticketFieldsFor(attendee: BookingAttendee) {
	return applyLogic(
		ticketCustomFields.value,
		props.logicRules.Ticket || [],
		{ ...attendee, ticket_type: String(attendee.ticket_type ?? "") },
		attendee.custom_fields || {},
	)
}

const eventId = computed(() =>
	props.availableTicketTypes[0]?.event ? String(props.availableTicketTypes[0].event) : null,
)

// --- CURRENCY ---
const {
	baseCurrency,
	currency,
	currencies,
	notSoldIn,
	setCurrency,
	undo: undoCurrency,
	dismissUndo,
	removedMessage,
} = useCurrencySwitch(
	computed(() => props.availableTicketTypes),
	computed(() => props.availableAddOns),
	attendees,
)

function inCurrency<T extends AvailableTicketType | AvailableAddOn>(item: T) {
	if (!notSoldIn(item)) return pricedIn(item, currency.value)
	return { ...item, price_note: __("{0} only", [baseCurrency.value]) }
}

const ticketTypes = computed(() => props.availableTicketTypes.map(inCurrency))
const addOns = computed(() => props.availableAddOns.map(inCurrency))
const ticketTypesMap = computed(() =>
	Object.fromEntries(ticketTypes.value.map((t) => [String(t.name), t])),
)
const addOnsMap = computed(() => Object.fromEntries(addOns.value.map((a) => [a.name, a])))

const isOfflineGateway = (gateway: string) => props.offlineMethods.some((m) => m.title === gateway)
const offlineGatewayTitles = computed(() => props.offlineMethods.map((m) => m.title))
// Offline methods settle in the event's own currency.
const gateways = computed(() =>
	currency.value === baseCurrency.value
		? props.paymentGateways
		: props.paymentGateways.filter((g) => !isOfflineGateway(g)),
)
const selectedGateway = ref<string | null>(null)
const showSummarySheet = ref(false)
watch(
	gateways,
	(list) => {
		if (!selectedGateway.value || !list.includes(selectedGateway.value))
			selectedGateway.value = list[0] ?? null
	},
	{ immediate: true },
)

// --- QUANTITIES ---
// Attendees are the source of truth: a ticket type's quantity is its attendee count.
const quantities = computed(() => {
	const counts: Record<string, number> = {}
	for (const attendee of attendees.value)
		counts[String(attendee.ticket_type)] = (counts[String(attendee.ticket_type)] ?? 0) + 1
	return counts
})

// Ticket types with a limit are the only ones a hold reserves.
const heldQuantities = computed(() => {
	const limited = new Set(
		props.availableTicketTypes.filter((t) => t.max_tickets_available).map((t) => String(t.name)),
	)
	return Object.fromEntries(Object.entries(quantities.value).filter(([name]) => limited.has(name)))
})

const { holdToken, secondsLeft, expired, holdError, holdAgain, keepHold } = useTicketHold(
	props.eventRoute,
	eventId,
	heldQuantities,
)
const holdErrorMessage = computed(() => serverErrorMessage(holdError.value))

function createAttendee(ticketType: string): BookingAttendee {
	attendeeIdCounter.value++
	const attendee: BookingAttendee = {
		id: attendeeIdCounter.value,
		first_name: "",
		last_name: "",
		email: "",
		ticket_type: ticketType,
		// The first ticket defaults to the person registering.
		is_me: !attendees.value.some((other) => other.is_me),
		add_ons: {},
		custom_fields: {},
	}
	for (const addOn of props.availableAddOns)
		attendee.add_ons![addOn.name] = { selected: false, option: addOn.options?.[0] ?? null }
	for (const field of ticketCustomFields.value) {
		if (field.default_value) attendee.custom_fields![field.fieldname] = field.default_value
	}
	return attendee
}

function changeQuantity(ticketType: AvailableTicketType, delta: number) {
	dismissUndo()
	const name = String(ticketType.name)
	if (delta > 0) attendees.value.push(createAttendee(name))
	else {
		const index = attendees.value.findLastIndex((attendee) => String(attendee.ticket_type) === name)
		if (index >= 0) attendees.value.splice(index, 1)
	}
}

watchEffect(() => {
	for (const attendee of attendees.value) {
		if (!attendee.is_me) continue
		attendee.first_name = me.first_name
		attendee.last_name = me.last_name
		attendee.email = me.email
	}
})

// --- PRICING ---
const pricing = useOrderPricing({
	attendees,
	ticketTypesMap,
	addOnsMap,
	taxSettings: () => props.taxSettings,
	currency,
	eventId,
	guestEmail: () => (props.isGuestMode ? billing.value.buyer_email || guestEmail.value : null),
})
const { netAmount, discountAmount, tax, taxAmount, total, totalBeforeDiscount } = pricing
const coupon = reactive(pricing.coupon)

// The typed code, or the automatic offer's name when no code is applied.
const discountName = computed(() => (coupon.applied ? coupon.appliedCode : coupon.offerName))
const summaryProps = computed(() => ({
	lines: pricing.lines.value,
	totals: {
		subtotal: netAmount.value,
		discount: discountAmount.value,
		tax: taxAmount.value,
		total: total.value,
		before: totalBeforeDiscount.value,
	},
	currency: currency.value,
	taxLabel: tax.value.label,
	taxPercentage: tax.value.percentage,
	taxInclusive: tax.value.inclusive,
	discountLabel: discountName.value ? __("Discount · {0}", [discountName.value]) : __("Discount"),
}))

const showCoupon = computed(() => netAmount.value > 0 || coupon.applied)
const couponProps = computed(() => ({
	applied: coupon.applied,
	appliedNote: pricing.couponNote.value,
	error: coupon.error,
	loading: coupon.loading,
}))

const countLabel = computed(() => {
	const count = attendees.value.length
	if (!count) return __("No tickets selected")
	const tickets = count === 1 ? __("1 ticket") : __("{0} tickets", [count])
	if (total.value <= 0) return `${tickets} · ${__("Free")}`
	return tax.value.apply ? `${tickets} · ${__("incl. {0}", [__(tax.value.label)])}` : tickets
})

// --- STEPS ---
const validation = useRegistrationValidation({
	me,
	attendees,
	ticketFieldsFor,
	bookingCustomFields,
	bookingCustomFieldsData,
	billing,
	selectedGateway,
	invoiceShown: () => tax.value.apply,
	taxIsGst: () => isGstLabel(tax.value.label),
	phoneRequired: () => props.isGuestMode && isPhoneOtp.value,
	lastNameRequired: () => isZoomEvent.value,
})
const { meErrors, attendeeErrorList, detailsErrors } = validation

const steps = computed(() =>
	buildSteps({
		ticketCount: attendees.value.length,
		completeAttendees: validation.completeAttendees.value,
		paid: netAmount.value > 0,
		payable: total.value > 0,
		totalLabel: formatWholePriceOrFree(total.value, currency.value),
	}),
)
const { current, direction, step, isLast, tried, go, markTried } = useRegistrationSteps(steps)
const stepCopy = computed(() =>
	copyFor(step.value.id, {
		free: Boolean(props.eventDetails.free_event),
		paid: netAmount.value > 0,
	}),
)

const stepErrors = computed(() => validation.errorsFor(step.value.id))
const showStepError = computed(() => tried.value && stepErrors.value.length > 0)
const stepErrorMessage = computed(() => validation.summarize(stepErrors.value))

const nextStep = computed(() => steps.value[current.value + 1])
const totalLabel = computed(() => formatWholePriceOrFree(total.value, currency.value))
const ctaLabel = computed(() => {
	if (nextStep.value?.id === "summary") return __("Review booking")
	if (nextStep.value) return __("Continue to {0}", [nextStep.value.label.toLowerCase()])
	if (placing.value) return __("Processing...")
	if (total.value > 0) return __("Proceed to pay {0}", [totalLabel.value])
	return isZoomEvent.value || props.eventDetails.free_event ? __("Register") : __("Book Tickets")
})
const mobileCtaLabel = computed(() => {
	if (nextStep.value?.id === "summary") return __("Review")
	if (nextStep.value) return __("Continue")
	return total.value > 0 && !placing.value ? __("Pay {0}", [totalLabel.value]) : ctaLabel.value
})

function goToStep(id: RegistrationStepId) {
	go(steps.value.findIndex((candidate) => candidate.id === id))
}

function next() {
	if (requiresLogin.value) return openLoginDialog()
	if (stepErrors.value.length) {
		markTried()
		// After the errors render (and a mobile card opens), take the person to the first one.
		setTimeout(
			() => document.querySelector<HTMLElement>("form [aria-invalid='true']")?.focus(),
			320,
		)
		return
	}
	if (isLast.value) submit()
	else go(current.value + 1)
}

function back() {
	if (current.value > 0) go(current.value - 1)
	else window.location.assign(eventPath(props.eventRoute))
}

// --- SUBMIT ---
const otpState = useGuestOtp(
	() => props.eventDetails.name,
	() => isPhoneOtp.value,
	() => (isPhoneOtp.value ? billing.value.buyer_phone : billing.value.buyer_email),
)
const otp = reactive(otpState)
watch(
	() => billing.value.buyer_phone,
	() => (otpState.phoneError.value = ""),
)
// The buyer starts as the person registering.
watch(
	() => step.value.id,
	(id) => {
		if (id !== "details") return
		billing.value.buyer_name ||= `${me.first_name} ${me.last_name}`.trim()
		billing.value.buyer_email ||= me.email
	},
)

const { submit, verifyOtp, submitOffline, offlineMethod, showOfflineDialog, completed, placing } =
	useBookingSubmit({
		buildPayload,
		total,
		gateways,
		selectedGateway,
		offlineMethods: () => props.offlineMethods,
		isGuest: () => props.isGuestMode,
		needsOtp: () => props.eventDetails.guest_verification_method !== "None",
		otp: otpState,
		keepHold,
	})
const submitting = computed(() => placing.value || otp.sending)

const activeOfflineSettings = computed(() =>
	offlineMethod.value
		? {
				label: offlineMethod.value.title,
				payment_details: offlineMethod.value.description,
				collect_payment_proof: offlineMethod.value.collect_payment_proof,
			}
		: {},
)
const activeOfflineCustomFields = computed(() => offlineMethod.value?.custom_fields || [])

function buildPayload() {
	const utmParameters = Object.entries(route.query)
		.filter(([key, value]) => key.toLowerCase().startsWith("utm_") && value)
		.map(([key, value]) => ({ utm_name: key, value: String(value) }))
	const guest = props.isGuestMode
	const { buyer_name, buyer_email, buyer_phone, invoice_requested, ...invoice } = billing.value
	const wantsInvoice = tax.value.apply && invoice_requested
	return {
		event: eventId.value,
		attendees: attendees.value.map((attendee) =>
			attendeePayload(attendee, ticketFieldsFor(attendee)),
		),
		coupon_code: coupon.appliedCode || null,
		booking_custom_fields: cleanCustomFields(
			bookingCustomFieldsData.value,
			bookingCustomFields.value,
		),
		utm_parameters: utmParameters.length ? utmParameters : null,
		currency: currency.value,
		buyer_name: buyer_name.trim(),
		buyer_email: buyer_email.trim(),
		buyer_phone: buyer_phone.trim() || null,
		// A guest's account is made for the buyer.
		guest_email: guest ? buyer_email.trim() : null,
		guest_full_name: guest ? buyer_name.trim() : null,
		guest_phone: guest && isPhoneOtp.value ? buyer_phone.trim() : null,
		invoice_requested: wantsInvoice,
		...(wantsInvoice ? trimmed(invoice) : {}),
		hold_token: holdToken.value,
	}
}

function trimmed(values: Record<string, string>) {
	return Object.fromEntries(
		Object.entries(values).map(([key, value]) => [key, value.trim() || null]),
	)
}

const successTitle = computed(() => {
	if (completed.value?.pendingVerification) return __("Booking received")
	return isZoomEvent.value ? __("Registration confirmed") : __("You're registered")
})

const successMessage = computed(() => {
	if (completed.value?.pendingVerification)
		return __("Your payment is awaiting verification. We'll email {0} once it's confirmed.", [
			billing.value.buyer_email,
		])
	if (isZoomEvent.value)
		return __("You'll receive an invite at {0} shortly.", [billing.value.buyer_email])
	return __("Your tickets have been sent to {0}.", [billing.value.buyer_email])
})

// --- LIFECYCLE ---
// The checkout header replaces the site header until the booking is done.
watch(completed, (done) => (siteHeaderHidden.value = !done), { immediate: true })
onUnmounted(() => (siteHeaderHidden.value = false))

function fillMeFromUser() {
	const user = userResource.data
	if (props.isGuestMode || !user || me.email) return
	me.first_name = user.first_name || ""
	me.last_name = user.last_name || ""
	me.email = user.email || ""
	if (attendees.value.length && !attendees.value.some((attendee) => attendee.is_me))
		attendees.value[0].is_me = true
}
watch(() => userResource.data, fillMeFromUser)

function defaultTicketType() {
	const preferred = props.eventDetails?.default_ticket_type
	const sellable = ticketTypes.value.filter((ticketType) => !ticketType.price_note)
	if (preferred && sellable.some((ticketType) => String(ticketType.name) === String(preferred)))
		return String(preferred)
	return String(sellable[0]?.name ?? "")
}

onMounted(async () => {
	await nextTick()
	fillMeFromUser()
	if (!attendees.value.length && ticketTypes.value.length)
		attendees.value = [createAttendee(defaultTicketType())]
	await pricing.coupon.applyFromLink()
})

// Every attendee keeps a slot for every add-on.
watch(
	() => props.availableAddOns,
	(newAddOns) => {
		for (const attendee of attendees.value) {
			attendee.add_ons ??= {}
			for (const addOn of newAddOns)
				attendee.add_ons[addOn.name] ??= { selected: false, option: addOn.options?.[0] ?? null }
		}
	},
	{ immediate: true, deep: true },
)

// A ticket type that stopped selling (or a stale stored one) drops its attendees.
watch(
	ticketTypes,
	(list) => {
		if (!list.length) return
		const available = new Set(list.map((ticketType) => String(ticketType.name)))
		const kept = attendees.value.filter((attendee) => available.has(String(attendee.ticket_type)))
		if (kept.length !== attendees.value.length) attendees.value = kept
	},
	{ immediate: true },
)

watch(
	bookingCustomFields,
	(fields) => {
		for (const field of fields) {
			if (field.default_value && !bookingCustomFieldsData.value[field.fieldname])
				bookingCustomFieldsData.value[field.fieldname] = field.default_value
		}
	},
	{ immediate: true },
)
</script>

<style>
.step-rise-enter-active,
.step-slide-enter-active {
	transition:
		opacity 280ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 280ms cubic-bezier(0.23, 1, 0.32, 1);
}
.step-rise-leave-active,
.step-slide-leave-active {
	transition: opacity 120ms ease-out;
}
.step-rise-enter-from,
.step-slide-enter-from,
.step-rise-leave-to,
.step-slide-leave-to {
	opacity: 0;
}
.step-rise-enter-from {
	transform: translateY(calc(var(--direction, 1) * 8px));
}
.step-slide-enter-from {
	transform: translateX(calc(var(--direction, 1) * 16px));
}
@media (prefers-reduced-motion: reduce) {
	.step-rise-enter-from,
	.step-slide-enter-from {
		transform: none;
	}
}
</style>
