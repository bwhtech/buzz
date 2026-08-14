import type { EventDetail, MyEvents } from "@/types"
import { createResource, useCall } from "frappe-ui"

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this user's feed to IndexedDB past a logout.
export function useMyEvents() {
	return useCall<MyEvents>({
		url: "/api/v2/method/buzz.api.events.get_my_events",
	})
}

export const createEvent = createResource<{ name: string; title: string }>({
	url: "buzz.api.events.create_event",
})

/** One event with everything its manage page edits. Per page, so it is not a singleton. */
export function eventDetail(event: string) {
	return createResource<EventDetail>({
		url: "buzz.api.events.get_event",
		params: { event },
		auto: true,
	})
}

/**
 * Save edits back onto an event.
 *
 * `set_value` takes a fieldname-to-value map, so the whole form travels as one write —
 * and the team permission hooks guard Buzz Event, which is why this needs no endpoint of
 * its own.
 */
export const updateEvent = createResource({ url: "frappe.client.set_value" })
