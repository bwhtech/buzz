import { refDebounced } from "@vueuse/core"
import { useCall } from "frappe-ui"
import { computed, type Ref, ref, watch } from "vue"

import type { EventProposals, ProposalListItem } from "@/types"

export const PROPOSALS_PAGE_SIZE = 20

export type ProposalOrder = "desc" | "asc"

/**
 * One event's talk proposals, fetched a page at a time.
 *
 * Search, status filter and sort live on the server, so the browser only ever holds the
 * pages it has walked down to. A page appends; a change of any control starts over.
 *
 * The controls are owned by the caller, so they can live in the query string and a
 * filtered pipeline survives a reload.
 */
export function useEventProposals(
	event: string,
	search: Ref<string>,
	order: Ref<ProposalOrder>,
	statuses: Ref<string[]>,
) {
	// Typing rewrites the URL, and every rewrite is a request — wait for the pause.
	const debouncedSearch = refDebounced(search, 300)
	const start = ref(0)
	const proposals = ref<ProposalListItem[]>([])

	const page = useCall<EventProposals, Record<string, string | number>>({
		url: "/api/v2/method/buzz.api.proposals.get_event_proposals",
		params: () => ({
			event,
			search: debouncedSearch.value.trim(),
			// Comma-joined, the shape the query string already holds them in.
			statuses: statuses.value.join(","),
			order: order.value,
			start: start.value,
			limit: PROPOSALS_PAGE_SIZE,
		}),
		// Off by default, so without this a new page or search would never be fetched.
		refetch: true,
		onSuccess: (data) => {
			if (start.value === 0) {
				proposals.value = data.proposals
				return
			}
			// The offset is taken against a live list: a proposal submitted since the first
			// page shifts every later one down, and the row on the boundary arrives twice.
			const seen = new Set(proposals.value.map((proposal) => proposal.name))
			proposals.value = [
				...proposals.value,
				...data.proposals.filter((proposal) => !seen.has(proposal.name)),
			]
		},
	})

	// Sync, so the offset is back at zero before useCall's own watcher rebuilds the URL —
	// a pre-flush reset lets the stale offset go out as a request that is aborted a tick later.
	watch(
		[debouncedSearch, order, statuses],
		() => {
			start.value = 0
			proposals.value = []
		},
		{ flush: "sync" },
	)

	/**
	 * Carries a status change into the list without refetching.
	 *
	 * Refetching would not do it: past the first page `onSuccess` appends what it does
	 * not already hold, so the changed row is discarded as a duplicate and the stale one
	 * stays on screen. A row that no longer answers the active filter leaves the list.
	 */
	const applyStatus = (name: string, status: string) => {
		const matchesFilter = !statuses.value.length || statuses.value.includes(status)
		proposals.value = matchesFilter
			? proposals.value.map((proposal) =>
					proposal.name === name ? { ...proposal, status } : proposal,
				)
			: proposals.value.filter((proposal) => proposal.name !== name)
	}

	// The offset is what the browser already holds, not the page number it is on. A row
	// that a status change took out of the filter is gone from the server's results too,
	// so every row behind it moved down one — counting pages would step over them.
	const loadMore = () => {
		if (page.loading || !page.data?.has_next_page) return
		start.value = proposals.value.length
	}

	return {
		proposals,
		applyStatus,
		loadMore,
		page,
		// The first page is the only one that leaves the list empty while it loads.
		loadingFirstPage: computed(() => page.loading && start.value === 0),
		loadingMore: computed(() => page.loading && start.value > 0),
	}
}
