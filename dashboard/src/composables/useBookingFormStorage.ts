import { useStorage } from "@vueuse/core"

import type { BookingAttendee } from "@/types"

/**
 * Composable for managing booking form localStorage data
 * This allows components to access and clear booking form data stored in localStorage
 * @param {string} eventRoute - The event route to scope the storage keys
 */
export function useBookingFormStorage(eventRoute: string) {
	if (!eventRoute) {
		throw new Error("eventRoute is required for useBookingFormStorage")
	}

	// Scope storage keys to the specific event route
	const storageKeyPrefix = `event-booking-${eventRoute}`
	const attendees = useStorage<BookingAttendee[]>(`${storageKeyPrefix}-attendees`, [], undefined, {
		deep: true,
	})
	const attendeeIdCounter = useStorage(`${storageKeyPrefix}-counter`, 0)
	const bookingCustomFields = useStorage<Record<string, any>>(
		`${storageKeyPrefix}-custom-fields`,
		{},
	)

	const guestFirstName = useStorage(`${storageKeyPrefix}-guest-first-name`, "")
	const guestLastName = useStorage(`${storageKeyPrefix}-guest-last-name`, "")
	const guestEmail = useStorage(`${storageKeyPrefix}-guest-email`, "")
	// Who pays, and the tax invoice they asked for; saved on the Event Booking as is.
	const billing = useStorage(`${storageKeyPrefix}-billing`, emptyBilling(), undefined, {
		mergeDefaults: true,
	})

	/**
	 * Clear all stored booking form data
	 * This should be called when payment is successful
	 */
	const clearStoredData = () => {
		attendees.value = []
		attendeeIdCounter.value = 0
		bookingCustomFields.value = {}
		guestFirstName.value = ""
		guestLastName.value = ""
		guestEmail.value = ""
		billing.value = emptyBilling()
	}

	/**
	 * Check if there's any stored booking data
	 */
	const hasStoredData = () => {
		return attendees.value.length > 0 || Object.keys(bookingCustomFields.value).length > 0
	}

	return {
		attendees,
		attendeeIdCounter,
		bookingCustomFields,
		guestFirstName,
		guestLastName,
		guestEmail,
		billing,
		clearStoredData,
		hasStoredData,
	}
}

export function emptyBilling() {
	return {
		buyer_name: "",
		buyer_email: "",
		buyer_phone: "",
		invoice_requested: false,
		tax_id: "",
		business_name: "",
		billing_address: "",
		billing_state: "",
	}
}

export type BillingDetails = ReturnType<typeof emptyBilling>
