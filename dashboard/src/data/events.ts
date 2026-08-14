import type { MyEvent, MyEvents } from "@/types"
import { createResource, useCall } from "frappe-ui"
import { type Ref, computed } from "vue"

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

/**
 * One event out of the feed the dashboard loads for this page.
 *
 * The feed carries every event the user hosts or holds a ticket to, so the manage
 * pages can name an event without a second round trip. Undefined while the feed
 * loads, and for an event the user cannot see at all.
 */
export function useMyEvent(eventId: Ref<string>) {
	const myEvents = useMyEvents()
	return computed((): MyEvent | undefined => {
		const events = myEvents.data
		if (!events) return undefined
		return [...events.upcoming, ...events.past].find((event) => event.name === eventId.value)
	})
}
