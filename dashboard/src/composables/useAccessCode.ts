import { nextTick, type Ref, watch } from "vue"

import type { AvailableTicketType, BookingAttendee } from "@/types"

/**
 * When the applied code changes, the booking data is fetched again. Once it arrives,
 * attendees whose ticket type is no longer on offer are removed.
 */
export function useAccessCode(
	appliedCode: Ref<string>,
	attendees: Ref<BookingAttendee[]>,
	listedTicketTypes: () => AvailableTicketType[],
	onChange: (code: string) => Promise<unknown>,
) {
	function removeUnlistedAttendees() {
		const listed = new Set(listedTicketTypes().map((ticketType) => String(ticketType.name)))
		attendees.value = attendees.value.filter((attendee) => listed.has(String(attendee.ticket_type)))
		if (attendees.value.length && !attendees.value.some((attendee) => attendee.is_me))
			attendees.value[0].is_me = true
	}

	watch(appliedCode, (code) => {
		onChange(code)
			.then(() => nextTick())
			.then(removeUnlistedAttendees)
	})
}
