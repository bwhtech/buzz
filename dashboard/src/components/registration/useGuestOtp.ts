import { toast, useCall } from "frappe-ui"
import { computed, onUnmounted, ref } from "vue"

import { serverErrorMessage } from "@/utils/serverError"

const RESEND_COOLDOWN_SECONDS = 30

/** Sends a guest the code that proves they own the email or phone they booked with. */
export function useGuestOtp(event: () => string, isPhone: () => boolean, identifier: () => string) {
	const open = ref(false)
	const code = ref("")
	const error = ref("")
	const phoneError = ref("")
	const cooldown = ref(0)
	let timer: ReturnType<typeof setInterval> | undefined

	const sendCall = useCall<unknown, { event: string; identifier: string }>({
		url: "/api/v2/method/buzz.api.booking.send_guest_booking_otp",
		method: "POST",
		immediate: false,
		onSuccess: () => {
			open.value = true
			startCooldown()
			toast.success(
				isPhone()
					? __("Verification code sent to your phone")
					: __("Verification code sent to your email"),
			)
		},
		onError: (sendError) => {
			const message = serverErrorMessage(sendError) || __("Failed to send verification code")
			// Under the phone field, not in a toast the person has to remember while retyping.
			if (isPhone()) phoneError.value = message
			else toast.error(message)
		},
	})

	function startCooldown() {
		cooldown.value = RESEND_COOLDOWN_SECONDS
		clearInterval(timer)
		timer = setInterval(() => {
			cooldown.value--
			if (cooldown.value <= 0) clearInterval(timer)
		}, 1000)
	}

	function send() {
		phoneError.value = ""
		sendCall.submit({ event: event(), identifier: identifier().trim() })
	}

	function resend() {
		if (sendCall.loading || cooldown.value > 0) return
		code.value = ""
		send()
	}

	function reset() {
		open.value = false
		code.value = ""
		error.value = ""
		cooldown.value = 0
		clearInterval(timer)
	}

	// A lockout or an expired code means starting over; anything else is a retry.
	function fail(message: string) {
		code.value = ""
		if (message.includes("Too many") || message.includes("expired")) {
			open.value = false
			toast.error(message)
		} else {
			error.value = message
		}
	}

	onUnmounted(() => clearInterval(timer))

	return {
		open,
		code,
		error,
		phoneError,
		cooldown,
		sending: computed(() => sendCall.loading),
		send,
		resend,
		reset,
		fail,
	}
}
