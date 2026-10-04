import { refDebounced } from "@vueuse/core"
import { useCall } from "frappe-ui"
import { computed, type Ref, ref, watch } from "vue"

import { type Condition, keepsStatus } from "@/components/common/filters"
import type { ListOrder } from "@/composables/useListQuery"
import type { EventEnquiries, EventEnquiryItem } from "@/types"

const PAGE_SIZE = 20

/**
 * One event's sponsorship enquiries, a page at a time, the way useEventProposals walks talks.
 * Search, filters and sort run on the server; a change of any control starts over.
 */
export function useEventEnquiries(
	event: string,
	search: Ref<string>,
	order: Ref<ListOrder>,
	conditions: Ref<Condition[]>,
) {
	const debouncedSearch = refDebounced(search, 300)
	const start = ref(0)
	const enquiries = ref<EventEnquiryItem[]>([])

	const page = useCall<EventEnquiries, Record<string, string | number>>({
		url: "/api/v2/method/buzz.api.sponsorships.get_event_sponsorship_enquiries",
		params: () => ({
			event,
			search: debouncedSearch.value.trim(),
			filters: JSON.stringify(conditions.value),
			order: order.value,
			start: start.value,
			limit: PAGE_SIZE,
		}),
		refetch: true,
		onSuccess: (data) => {
			if (start.value === 0) {
				enquiries.value = data.enquiries
				return
			}
			// A new enquiry since the first page shifts the offset; skip the repeated boundary row.
			const seen = new Set(enquiries.value.map((row) => row.name))
			enquiries.value = [...enquiries.value, ...data.enquiries.filter((row) => !seen.has(row.name))]
		},
	})

	// Sync, so the offset is zero before useCall rebuilds the URL for the new controls.
	watch(
		[debouncedSearch, order, conditions],
		() => {
			start.value = 0
			enquiries.value = []
		},
		{ flush: "sync" },
	)

	// Patched in place: past the first page a refetch would drop the changed row as a duplicate.
	const applyStatus = (name: string, status: string) => {
		const matchesFilter = keepsStatus(conditions.value, status)
		enquiries.value = matchesFilter
			? enquiries.value.map((row) => (row.name === name ? { ...row, status } : row))
			: enquiries.value.filter((row) => row.name !== name)
	}

	const loadMore = () => {
		if (page.loading || !page.data?.has_next_page) return
		start.value = enquiries.value.length
	}

	return {
		enquiries,
		applyStatus,
		loadMore,
		page,
		loadingFirstPage: computed(() => page.loading && start.value === 0),
		loadingMore: computed(() => page.loading && start.value > 0),
	}
}
