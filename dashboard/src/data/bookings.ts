import { useCall } from "frappe-ui"

import type { BookingSummary } from "@/types"

/**
 * One booking as a receipt, scoped by read permission rather than by who booked it — a
 * ticket holder can open the booking behind their ticket even when someone else paid.
 *
 * v2 path: useCall reads the payload from `data`, which /api/method names `message`.
 * Uncached: cacheKey would persist this user's bookings to IndexedDB past a logout.
 */
export function useBookingSummary(booking: () => string | undefined) {
	return useCall<BookingSummary, { booking_id: string }>({
		url: "/api/v2/method/buzz.api.booking.get_booking_summary",
		params: () => ({ booking_id: booking() || "" }),
		// A caller that already has its booking fetches on mount; the ticket drawer mounts
		// before one is picked, so there the first fetch waits for the id.
		immediate: Boolean(booking()),
		refetch: true,
	})
}
