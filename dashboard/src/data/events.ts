import type { MyEvents } from "@/types"
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
