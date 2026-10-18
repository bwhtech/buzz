import { computed, type Ref } from "vue"

import type { BillingDetails } from "@/composables/useBookingFormStorage"
import type { FrappeField } from "@/composables/useCustomFields"
import type { BookingAttendee } from "@/types"

import {
	attendeeErrors,
	type AttendeeErrors,
	type AttendeeIdentity,
	isValidEmail,
} from "./attendeeValidation"
import type { RegistrationStepId } from "./useRegistrationSteps"

// Fields that show their error under the input; the rest are named under the button.
const INLINE_FIELDS = new Set([
	"first_name",
	"last_name",
	"email",
	"buyer_name",
	"buyer_email",
	"buyer_phone",
	"tax_id",
	"business_name",
])
const GSTIN_LENGTH = 15

interface ValidationInputs {
	me: AttendeeIdentity
	attendees: Ref<BookingAttendee[]>
	ticketCustomFields: Ref<FrappeField[]>
	bookingCustomFields: Ref<FrappeField[]>
	bookingCustomFieldsData: Ref<Record<string, any>>
	billing: Ref<BillingDetails>
	invoiceShown: () => boolean
	taxIsGst: () => boolean
	selectedGateway: Ref<string | null>
	phoneRequired: () => boolean
	lastNameRequired: () => boolean
}

export function useRegistrationValidation(inputs: ValidationInputs) {
	const meErrors = computed(() =>
		attendeeErrors({ id: 0, ...inputs.me }, inputs.lastNameRequired(), []),
	)

	const attendeeErrorList = computed(() =>
		inputs.attendees.value.map((attendee) =>
			attendeeErrors(attendee, inputs.lastNameRequired(), inputs.ticketCustomFields.value),
		),
	)

	const completeAttendees = computed(
		() => attendeeErrorList.value.filter((errors) => !Object.keys(errors).length).length,
	)

	const detailsErrors = computed(() => {
		const billing = inputs.billing.value
		const errors: AttendeeErrors = {}
		if (!billing.buyer_name.trim()) errors.buyer_name = __("Enter your name")
		if (!isValidEmail(billing.buyer_email)) errors.buyer_email = __("Enter a valid email address")
		if (inputs.phoneRequired() && !billing.buyer_phone.trim())
			errors.buyer_phone = __("Enter a phone number")
		for (const field of inputs.bookingCustomFields.value) {
			const value = inputs.bookingCustomFieldsData.value[field.fieldname]
			if (field.mandatory && (value == null || !String(value).trim()))
				errors[field.fieldname] = __("{0} is required", [__(field.label)])
		}
		return { ...errors, ...invoiceErrors(billing) }
	})

	function invoiceErrors(billing: BillingDetails): AttendeeErrors {
		if (!inputs.invoiceShown() || !billing.invoice_requested) return {}
		const errors: AttendeeErrors = {}
		const taxId = billing.tax_id.trim()
		if (!taxId) errors.tax_id = __("Enter your tax ID")
		else if (inputs.taxIsGst() && taxId.length !== GSTIN_LENGTH)
			errors.tax_id = __("Enter a 15-character GSTIN")
		if (!billing.business_name.trim()) errors.business_name = __("Enter the business name")
		return errors
	}

	function errorsFor(stepId: RegistrationStepId): AttendeeErrors[] {
		if (stepId === "tickets")
			return inputs.attendees.value.length ? [] : [{ tickets: __("Pick at least one ticket") }]
		if (stepId === "attendees") {
			const forMe = inputs.attendees.value.some((attendee) => attendee.is_me)
				? [meErrors.value]
				: []
			return [...forMe, ...attendeeErrorList.value].filter((errors) => Object.keys(errors).length)
		}
		if (stepId === "details")
			return Object.keys(detailsErrors.value).length ? [detailsErrors.value] : []
		return inputs.selectedGateway.value ? [] : [{ payment: __("Choose a payment method") }]
	}

	// Names what isn't highlighted inline; otherwise points at the highlighted fields.
	function summarize(errors: AttendeeErrors[]) {
		const named = new Set(
			errors.flatMap((group) =>
				Object.entries(group)
					.filter(([field]) => !INLINE_FIELDS.has(field))
					.map(([, message]) => message),
			),
		)
		return named.size
			? [...named].slice(0, 3).join(" · ")
			: __("Complete the highlighted fields to continue")
	}

	return { meErrors, attendeeErrorList, completeAttendees, detailsErrors, errorsFor, summarize }
}
