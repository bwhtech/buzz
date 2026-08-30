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
