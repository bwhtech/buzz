import beepFailSound from "@/assets/audio/beep-fail.wav"
import beepSound from "@/assets/audio/beep.wav"
import type { TicketAddOnValue } from "@/types/Ticketing/TicketAddOnValue"
import { createResource, toast } from "frappe-ui"
import { type Ref, ref } from "vue"

interface ValidationTicket {
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

interface ValidationResult {
	message?: string
	error?: string
	ticket?: ValidationTicket
	payment_details?: PaymentDetails
}

interface TicketValidationState {
	isProcessingTicket: Ref<boolean>
	isCheckingIn: Ref<boolean>
	validationResult: Ref<ValidationResult | null>
	showTicketModal: Ref<boolean>
	validateTicket: (ticketId: string) => void
	checkInTicket: () => void
	clearResults: () => void
	closeModal: () => void
}

let ticketValidationState: TicketValidationState | null = null

const isProcessingTicket = ref(false)
const isCheckingIn = ref(false)
const validationResult = ref<ValidationResult | null>(null)
const showTicketModal = ref(false)

let lastToastMessage: string | null = null
let lastToastTime = 0
const TOAST_DEBOUNCE_MS = 500

const playSuccessSound = (): void => {
	const audio = new Audio(beepSound)
	audio.play()
}

const playErrorSound = (): void => {
	const audio = new Audio(beepFailSound)
	audio.play()
}

const showDebouncedToast = (
	message: string,
	type: "error" | "success" = "error",
): void => {
	const now = Date.now()
	if (lastToastMessage === message && now - lastToastTime < TOAST_DEBOUNCE_MS) {
		return
	}
	lastToastMessage = message
	lastToastTime = now

	if (type === "error") {
		toast.error(message)
	} else {
		toast.success(message)
	}
}

// Ticket validation resource
const validateTicketResource = createResource({
	url: "buzz.api.validate_ticket_for_checkin",
	onSuccess: (data: ValidationResult) => {
		validationResult.value = data
		showTicketModal.value = true
		playSuccessSound()
		isProcessingTicket.value = false
	},
	onError: (error: any) => {
		validationResult.value = null
		isProcessingTicket.value = false
		const errorData = JSON.stringify(error)

		if (errorData.includes("Ticket not found")) {
			showDebouncedToast("Ticket not found")
		} else if (
			errorData.includes(
				"This ticket is not confirmed and cannot be used for check-in",
			)
		) {
			showDebouncedToast(
				"This ticket is not confirmed and cannot be used for check-in",
			)
		} else if (errorData.includes("This ticket was already checked in today")) {
			showDebouncedToast("This ticket was already checked in today.")
		} else if (errorData.includes("cancelled")) {
			showDebouncedToast(
				"This ticket has been cancelled and cannot be checked in",
			)
		} else {
			showDebouncedToast("Error validating ticket")
		}
		playErrorSound()
	},
})

// Check-in resource
const checkInResource = createResource({
	url: "buzz.api.checkin_ticket",
	onSuccess: (data: ValidationResult) => {
		validationResult.value = data
		showTicketModal.value = false
		isCheckingIn.value = false
	},
	onError: (error: any) => {
		isCheckingIn.value = false
	},
})

export function useTicketValidation(): TicketValidationState {
	if (ticketValidationState) {
		return ticketValidationState
	}

	// Methods
	const validateTicket = (ticketId: string): void => {
		isProcessingTicket.value = true
		validateTicketResource.submit({ ticket_id: ticketId })
	}

	const checkInTicket = (): void => {
		if (!validationResult.value?.ticket?.id) return

		isCheckingIn.value = true
		checkInResource.submit({ ticket_id: validationResult.value.ticket.id })
	}

	const clearResults = (): void => {
		validationResult.value = null
		isProcessingTicket.value = false
		isCheckingIn.value = false
		showTicketModal.value = false
	}

	const closeModal = (): void => {
		showTicketModal.value = false
	}

	ticketValidationState = {
		// State
		isProcessingTicket,
		isCheckingIn,
		validationResult,
		showTicketModal,

		// Methods
		validateTicket,
		checkInTicket,
		clearResults,
		closeModal,
	}

	return ticketValidationState
}
