import { refDebounced } from "@vueuse/core"
import { useCall } from "frappe-ui"
import { computed, type Ref, ref, watch } from "vue"

import type { Condition } from "@/components/common/filters"
import type { ListOrder } from "@/composables/useListQuery"
import type { EventGuest, EventGuests } from "@/types"

export const GUESTS_PAGE_SIZE = 20

/**
 * One event's guest list, fetched a page at a time.
 *
 * Search, filters and sort live on the server: the browser only ever holds the pages it has
 * walked down to, so a five-hundred-guest event costs the same first paint as a five.
 * A page appends; a change of search or order starts the list over.
 *
 * Both controls are owned by the caller, so they can live in the query string and a
 * filtered list survives a reload.
 */
export function useEventGuests(
	event: string,
	search: Ref<string>,
	order: Ref<ListOrder>,
	conditions: Ref<Condition[]>,
	// The check-in page reads the same list through its own, stricter endpoint, narrowed to
	// who has or has not arrived ("1" / "0", empty for everyone).
	{
		url = "/api/v2/method/buzz.api.events.get_event_guests",
		checkedIn = ref(""),
		zone = ref(""),
	}: { url?: string; checkedIn?: Ref<string>; zone?: Ref<string> } = {},
) {
	// Typing rewrites the URL, and every rewrite is a request — wait for the pause.
	const debouncedSearch = refDebounced(search, 300)
	const start = ref(0)
	const guests = ref<EventGuest[]>([])

	const page = useCall<EventGuests, Record<string, string | number>>({
		url,
		params: () => ({
			event,
			search: debouncedSearch.value.trim(),
			filters: JSON.stringify(conditions.value),
			order: order.value,
			start: start.value,
			limit: GUESTS_PAGE_SIZE,
			checked_in: checkedIn.value,
			...(zone.value && { zone: zone.value }),
		}),
		// Off by default, so without this a new page or search would never be fetched.
		refetch: true,
		onSuccess: (data) => {
			if (start.value === 0) {
				guests.value = data.guests
				return
			}
			// The offset is taken against a live list: a ticket raised since the first page
			// shifts every later one down, and the row on the boundary arrives twice.
			const seen = new Set(guests.value.map((guest) => guest.name))
			guests.value = [...guests.value, ...data.guests.filter((guest) => !seen.has(guest.name))]
		},
	})

	// One ticket by name, through the same permission check, for a link to a row not loaded.
	const lookup = useCall<EventGuests, Record<string, string | number>>({ url, immediate: false })
	const fetchOne = async (name: string) =>
		(await lookup.submit({ event, name, limit: 1 }))?.guests[0] ?? null

	// Sync, so the offset is back at zero before useCall's own watcher rebuilds the URL —
	// a pre-flush reset lets the stale offset go out as a request that is aborted a tick later.
	watch([debouncedSearch, order, conditions, checkedIn, zone], () => (start.value = 0), {
		flush: "sync",
	})

	const loadMore = () => {
		if (page.loading || !page.data?.has_next_page) return
		start.value += GUESTS_PAGE_SIZE
	}

	return {
		guests,
		fetchOne,
		loadMore,
		page,
		// The first page is the only one that leaves the list empty while it loads.
		loadingFirstPage: computed(() => page.loading && start.value === 0),
		loadingMore: computed(() => page.loading && start.value > 0),
		searchPending: computed(() => search.value.trim() !== debouncedSearch.value.trim()),
	}
}
