import { toast, useCall } from "frappe-ui"
import { type Ref, ref } from "vue"

import beepFailSound from "@/assets/audio/beep-fail.wav"
import beepSound from "@/assets/audio/beep.wav"
import type { TicketAddOnValue } from "@/types/Ticketing/TicketAddOnValue"
import { serverErrorMessage } from "@/utils/serverError"

export interface ValidationTicket {
	id: string
	attendee_name: string
	attendee_email: string
	event_title: string
	ticket_type: string
	venue: string
	start_date: string
	start_time: string
	end_date: string
	end_time: string
	is_checked_in: boolean
	check_in_time: string | null
	check_in_date?: string | null
	booking_id: string
	add_ons: ValidationAddOn[]
}

// Check-in responses join the add-on title onto each stored add-on value.
interface ValidationAddOn extends TicketAddOnValue {
	add_on_title?: string
}

interface PaymentDetails {
	name?: string
	amount?: number
	currency?: string
}

export interface ValidationResult {
	message?: string
	error?: string
	ticket?: ValidationTicket
	payment_details?: PaymentDetails
}

const isProcessingTicket = ref(false)
const validationResult = ref<ValidationResult | null>(null)

let lastToastMessage: string | null = null
let lastToastTime = 0
const TOAST_DEBOUNCE_MS = 500

const playSound = (sound: string): void => {
	new Audio(sound).play()
}

const showDebouncedToast = (message: string): void => {
	const now = Date.now()
	if (lastToastMessage === message && now - lastToastTime < TOAST_DEBOUNCE_MS) return
	lastToastMessage = message
	lastToastTime = now
	toast.error(message)
}

const validateTicketResource = useCall<ValidationResult, { ticket_id: string }>({
	url: "/api/v2/method/buzz.api.checkin.validate_ticket_for_checkin",
	method: "POST",
	immediate: false,
	onSuccess: (data) => {
		validationResult.value = data
		isProcessingTicket.value = false
		playSound(beepSound)
	},
	onError: (error) => {
		validationResult.value = null
		isProcessingTicket.value = false
		showDebouncedToast(serverErrorMessage(error) || __("Error validating ticket"))
		playSound(beepFailSound)
	},
})

const validateTicket = (ticketId: string): void => {
	isProcessingTicket.value = true
	validateTicketResource.submit({ ticket_id: ticketId })
}

/** Scan state shared by the scanner and the page that opens the scanned guest. */
export function useTicketValidation(): {
	isProcessingTicket: Ref<boolean>
	validationResult: Ref<ValidationResult | null>
	validateTicket: (ticketId: string) => void
} {
	return { isProcessingTicket, validationResult, validateTicket }
}
