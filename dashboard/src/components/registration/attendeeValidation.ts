import type { FrappeField } from "@/composables/useCustomFields"
import type { BookingAttendee } from "@/types"

export type AttendeeErrors = Record<string, string>

export interface AttendeeIdentity {
	first_name: string
	last_name: string
	email: string
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const isValidEmail = (email?: string) => EMAIL_PATTERN.test((email ?? "").trim())

const isBlank = (value: unknown) => value == null || !String(value).trim()

export function attendeeErrors(
	attendee: BookingAttendee,
	lastNameRequired: boolean,
	customFields: FrappeField[],
): AttendeeErrors {
	const errors: AttendeeErrors = {}
	if (isBlank(attendee.first_name)) errors.first_name = __("Enter a first name")
	if (lastNameRequired && isBlank(attendee.last_name)) errors.last_name = __("Enter a last name")
	if (!isValidEmail(attendee.email)) errors.email = __("Enter a valid email address")
	for (const field of customFields) {
		if (field.mandatory && isBlank(attendee.custom_fields?.[field.fieldname]))
			errors[field.fieldname] = __("{0} is required", [__(field.label)])
	}
	return errors
}
