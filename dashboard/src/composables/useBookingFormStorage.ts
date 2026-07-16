import type { BookingAttendee } from "@/types"
import { useStorage } from "@vueuse/core"

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
	const attendees = useStorage<BookingAttendee[]>(
		`${storageKeyPrefix}-attendees`,
		[],
		undefined,
		{ deep: true },
	)
	const attendeeIdCounter = useStorage(`${storageKeyPrefix}-counter`, 0)
	const bookingCustomFields = useStorage<Record<string, any>>(
		`${storageKeyPrefix}-custom-fields`,
		{},
	)

	const guestFirstName = useStorage(`${storageKeyPrefix}-guest-first-name`, "")
	const guestLastName = useStorage(`${storageKeyPrefix}-guest-last-name`, "")
	const guestEmail = useStorage(`${storageKeyPrefix}-guest-email`, "")
	const guestPhone = useStorage(`${storageKeyPrefix}-guest-phone`, "")

	const invoiceRequested = useStorage(`${storageKeyPrefix}-invoice-requested`, false)
	const taxId = useStorage(`${storageKeyPrefix}-tax-id`, "")
	const billingAddress = useStorage(`${storageKeyPrefix}-billing-address`, "")

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
		guestPhone.value = ""
		invoiceRequested.value = false
		taxId.value = ""
		billingAddress.value = ""
	}

	/**
	 * Check if there's any stored booking data
	 */
	const hasStoredData = () => {
		return (
			attendees.value.length > 0 ||
			Object.keys(bookingCustomFields.value).length > 0
		)
	}

	return {
		attendees,
		attendeeIdCounter,
		bookingCustomFields,
		guestFirstName,
		guestLastName,
		guestEmail,
		guestPhone,
		invoiceRequested,
		taxId,
		billingAddress,
		clearStoredData,
		hasStoredData,
	}
}
