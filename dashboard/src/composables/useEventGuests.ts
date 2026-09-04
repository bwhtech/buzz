import { refDebounced } from "@vueuse/core"
import { useCall } from "frappe-ui"
import { computed, type Ref, ref, watch } from "vue"

import type { EventGuest, EventGuests } from "@/types"

export const GUESTS_PAGE_SIZE = 20

export type GuestOrder = "desc" | "asc"

/**
 * One event's guest list, fetched a page at a time.
 *
 * Search and sort live on the server: the browser only ever holds the pages it has
 * walked down to, so a five-hundred-guest event costs the same first paint as a five.
 * A page appends; a change of search or order starts the list over.
 *
 * Both controls are owned by the caller, so they can live in the query string and a
 * filtered list survives a reload.
 */
export function useEventGuests(
	event: string,
	search: Ref<string>,
	order: Ref<GuestOrder>,
	ticketTypes: Ref<string[]>,
) {
	// Typing rewrites the URL, and every rewrite is a request — wait for the pause.
	const debouncedSearch = refDebounced(search, 300)
	const start = ref(0)
	const guests = ref<EventGuest[]>([])

	const page = useCall<EventGuests, Record<string, string | number>>({
		url: "/api/v2/method/buzz.api.events.get_event_guests",
		params: () => ({
			event,
			search: debouncedSearch.value.trim(),
			// Comma-joined, the shape the query string already holds them in.
			ticket_types: ticketTypes.value.join(","),
			order: order.value,
			start: start.value,
			limit: GUESTS_PAGE_SIZE,
		}),
		// Off by default, so without this a new page or search would never be fetched.
		refetch: true,
		onSuccess: (data) => {
			guests.value = start.value === 0 ? data.guests : [...guests.value, ...data.guests]
		},
	})

	watch([debouncedSearch, order, ticketTypes], () => {
		start.value = 0
		guests.value = []
	})

	const loadMore = () => {
		if (page.loading || !page.data?.has_next_page) return
		start.value += GUESTS_PAGE_SIZE
	}

	return {
		guests,
		loadMore,
		page,
		// The first page is the only one that leaves the list empty while it loads.
		loadingFirstPage: computed(() => page.loading && start.value === 0),
		loadingMore: computed(() => page.loading && start.value > 0),
	}
}
