import { computed, type Ref } from "vue"

import type { FrappeField } from "@/composables/useCustomFields"
import type { BookingAttendee } from "@/types"

import { attendeeErrors, type AttendeeErrors, type AttendeeIdentity } from "./attendeeValidation"
import type { RegistrationStepId } from "./useRegistrationSteps"

// Fields that show their error under the input; the rest are named under the button.
const INLINE_FIELDS = new Set(["first_name", "last_name", "email", "phone", "billing_address"])

interface ValidationInputs {
	me: AttendeeIdentity & { phone: string }
	attendees: Ref<BookingAttendee[]>
	ticketCustomFields: Ref<FrappeField[]>
	bookingCustomFields: Ref<FrappeField[]>
	bookingCustomFieldsData: Ref<Record<string, any>>
	invoiceRequested: Ref<boolean>
	billingAddress: Ref<string>
	selectedGateway: Ref<string | null>
	isGuest: () => boolean
	needsPhone: () => boolean
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
		const errors: AttendeeErrors = inputs.isGuest() ? { ...meErrors.value } : {}
		if (inputs.isGuest() && inputs.needsPhone() && !inputs.me.phone.trim())
			errors.phone = __("Enter a phone number")
		for (const field of inputs.bookingCustomFields.value) {
			const value = inputs.bookingCustomFieldsData.value[field.fieldname]
			if (field.mandatory && (value == null || !String(value).trim()))
				errors[field.fieldname] = __("{0} is required", [__(field.label)])
		}
		if (inputs.invoiceRequested.value && !inputs.billingAddress.value?.trim())
			errors.billing_address = __("Enter a billing address")
		return errors
	})

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
