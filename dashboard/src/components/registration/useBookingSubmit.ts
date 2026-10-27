import { toast, useCall } from "frappe-ui"
import { computed, ref, type Ref } from "vue"
import { useRouter } from "vue-router"

import type { FrappeField } from "@/composables/useCustomFields"
import type { BookingAttendee, OfflineMethod } from "@/types"
import {
	type BookingSubmitResponse,
	resolveBookingSuccessAction,
} from "@/utils/bookingSuccessRedirect"
import { clearBookingCache } from "@/utils/index"
import { serverErrorMessage } from "@/utils/serverError"

import type { useGuestOtp } from "./useGuestOtp"

type Payload = Record<string, any>

interface SubmitInputs {
	buildPayload: () => Payload
	total: Ref<number>
	gateways: Ref<string[]>
	selectedGateway: Ref<string | null>
	offlineMethods: () => OfflineMethod[]
	isGuest: () => boolean
	needsOtp: () => boolean
	otp: ReturnType<typeof useGuestOtp>
	keepHold: () => void
}

/**
 * Places the booking: verifies a guest first when the event asks for it, collects offline
 * payment details when that's the method, then hands off to the gateway or the result page.
 */
export function useBookingSubmit(inputs: SubmitInputs) {
	const router = useRouter()
	const { otp } = inputs

	const offlineMethod = ref<OfflineMethod | null>(null)
	const pendingPayload = ref<Payload | null>(null)
	const completed = ref<{
		bookingName: string
		pendingVerification: boolean
		approvalPending: boolean
	} | null>(null)

	const processBooking = useCall<BookingSubmitResponse, { booking: Payload }>({
		url: "/api/v2/method/buzz.api.booking.process_booking",
		method: "POST",
		immediate: false,
	})

	function submit() {
		if (processBooking.loading) return
		const payload = inputs.buildPayload()
		pendingPayload.value = payload
		if (inputs.isGuest() && inputs.needsOtp()) otp.send()
		else pay(payload)
	}

	function verifyOtp() {
		if (!otp.code.value.trim()) {
			otp.error.value = __("Please enter the verification code")
			return
		}
		pay({ ...pendingPayload.value, otp: otp.code.value.trim() }, true)
	}

	function pay(payload: Payload, isOtpFlow = false) {
		const paid = inputs.total.value > 0
		const gateway = paid ? inputs.selectedGateway.value : (inputs.gateways.value[0] ?? null)
		const method = paid ? inputs.offlineMethods().find((m) => m.title === gateway) : undefined
		if (method) {
			pendingPayload.value = payload
			offlineMethod.value = method
			otp.open.value = false
			return
		}
		place(payload, gateway, isOtpFlow)
	}

	function submitOffline(details: { payment_proof?: { file_url?: string } }) {
		if (!pendingPayload.value || !offlineMethod.value) return
		const payload = {
			...pendingPayload.value,
			payment_proof: details?.payment_proof?.file_url || null,
			is_offline: true,
			offline_payment_method: offlineMethod.value.name ? String(offlineMethod.value.name) : null,
		}
		offlineMethod.value = null
		place(payload, null)
	}

	async function place(payload: Payload, paymentGateway: string | null, isOtpFlow = false) {
		const data = await processBooking
			.submit({ booking: { ...payload, payment_gateway: paymentGateway } })
			.catch(() => null)
		if (processBooking.error || !data) {
			const message = serverErrorMessage(processBooking.error) || __("Booking failed")
			if (isOtpFlow) otp.fail(message)
			else toast.error(message)
			return
		}

		inputs.keepHold()
		clearBookingCache()
		if (isOtpFlow) otp.reset()

		const action = resolveBookingSuccessAction(data, { isGuestMode: inputs.isGuest() })
		if (action.type === "external") window.location.href = action.url
		else if (action.type === "route") router.replace(action.path)
		else
			completed.value = {
				bookingName: action.bookingName,
				pendingVerification: action.pendingVerification,
				approvalPending: action.approvalPending,
			}
	}

	const showOfflineDialog = computed({
		get: () => Boolean(offlineMethod.value),
		set: (open) => !open && (offlineMethod.value = null),
	})

	return {
		submit,
		verifyOtp,
		submitOffline,
		offlineMethod,
		showOfflineDialog,
		completed,
		placing: computed(() => processBooking.loading),
	}
}

export function cleanCustomFields(values: Record<string, any> | undefined, fields: FrappeField[]) {
	const cleaned: Record<string, any> = {}
	for (const [fieldName, value] of Object.entries(values ?? {})) {
		const field = fields.find((candidate) => candidate.fieldname === fieldName)
		// Mandatory fields go through even when empty; validation already passed.
		if (field && (field.mandatory || (value != null && String(value).trim())))
			cleaned[fieldName] = value || ""
	}
	return Object.keys(cleaned).length ? cleaned : null
}

export function attendeePayload(attendee: BookingAttendee, ticketCustomFields: FrappeField[]) {
	const { is_me: _isMe, ...clean } = JSON.parse(JSON.stringify(attendee))
	clean.add_ons = Object.entries(clean.add_ons ?? {})
		.filter(([, state]: [string, any]) => state.selected)
		.map(([addOn, state]: [string, any]) => ({ add_on: addOn, value: state.option || true }))
	clean.custom_fields = cleanCustomFields(clean.custom_fields, ticketCustomFields)
	return clean
}
