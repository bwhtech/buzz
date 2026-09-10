import { createResource, useCall, useDoc } from "frappe-ui"

import type {
	EventDetail,
	EventHostRef,
	MyEvents,
	RegistrationTrend,
	VerificationMethods,
} from "@/types"

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this user's feed to IndexedDB past a logout.
export function useMyEvents(filters?: () => Record<string, string>) {
	return useCall<MyEvents, { filters: string }>({
		url: "/api/v2/method/buzz.api.events.get_my_events",
		// JSON in one param: a nested object on a GET serialises to "[object Object]".
		params: () => ({ filters: JSON.stringify(filters?.() || {}) }),
		// Off by default, so without this a filter change rewrites the URL and never refetches.
		refetch: true,
	})
}

export const createEvent = createResource<{ name: string; title: string }>({
	url: "buzz.api.events.create_event",
})

/** What the manage shell reads off the event itself: its title, and whether it is live. */
type EventShellDoc = { name: string; title: string; is_published: 0 | 1 }

/**
 * The event document, shared by everything that reads or flips its publish state.
 *
 * useDoc keys into frappe-ui's document store, so the shell's archived banner and the
 * setting that archives the event work off one reactive doc — a write through `setValue`
 * lands in both without either knowing about the other.
 */
export function useEventDoc(event: () => string) {
	// The empty string holds the initial fetch until the route param resolves.
	return useDoc<EventShellDoc>({ doctype: "Buzz Event", name: () => event() || "" })
}

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

/** Whether an event can take a route. Routes are the public URL namespace, so they are unique. */
export const checkEventRoute = createResource({ url: "buzz.api.events.check_event_route" })

/** Registrations per day for an event, for the card above its guest list. */
export function useRegistrationTrend(event: string) {
	return useCall<RegistrationTrend, { event: string }>({
		url: "/api/v2/method/buzz.api.events.get_event_registration_trend",
		params: { event },
	})
}

/**
 * Which verification methods this site can deliver a guest OTP over. Site configuration
 * rather than event data, so it is fetched when the settings dialog opens rather than
 * cached — an admin configuring email mid-session must not be answered from IndexedDB.
 */
export function useVerificationMethods() {
	return useCall<VerificationMethods>({
		url: "/api/v2/method/buzz.api.events.get_verification_methods",
		immediate: false,
	})
}

/** Add an organisation that has no team here as a co-host of the event. */
export function useAddCoHost() {
	return useCall<
		EventHostRef,
		{ event: string; host_name: string; logo?: string; by_line?: string; about?: string }
	>({
		url: "/api/v2/method/buzz.api.events.add_co_host",
		method: "POST",
		immediate: false,
	})
}

/** Drop a co-host from the event. The Event Host record itself is left alone. */
export function useRemoveCoHost() {
	return useCall<null, { event: string; host: string }>({
		url: "/api/v2/method/buzz.api.events.remove_co_host",
		method: "POST",
		immediate: false,
	})
}
