import { useCall } from "frappe-ui"

import type { BookingSummary } from "@/types"

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this user's bookings to IndexedDB past a logout.
export function useMyBookingSummaries(event: () => string) {
	return useCall<BookingSummary[], { event: string }>({
		url: "/api/v2/method/buzz.api.booking.get_my_booking_summaries",
		params: () => ({ event: event() }),
		// Off by default, so without this the drawer keeps the first event's bookings.
		refetch: true,
	})
}

/**
 * One booking as a receipt, scoped by read permission rather than by who booked it — a
 * ticket holder can open the booking behind their ticket even when someone else paid.
 */
export function useBookingSummary(booking: () => string | undefined) {
	return useCall<BookingSummary, { booking_id: string }>({
		url: "/api/v2/method/buzz.api.booking.get_booking_summary",
		params: () => ({ booking_id: booking() || "" }),
		// The drawer mounts before a ticket is picked, so the first fetch waits for the id.
		immediate: false,
		refetch: true,
	})
}
