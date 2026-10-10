import { refDebounced } from "@vueuse/core"
import { useCall } from "frappe-ui"
import type { Ref } from "vue"

import type { Condition } from "@/components/common/filters"
import type { ListOrder } from "@/composables/useListQuery"
import type { EnquiryDetail, EventSponsors, EventSponsorships } from "@/types"

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this user's inquiries to IndexedDB past a logout.
// Rows are only ever counted, so the sidebar and tab bar need no more than the key.
export function useMySponsorships() {
	return useCall<{ name: string }[]>({
		url: "/api/v2/method/buzz.api.sponsorships.get_user_sponsorship_inquiries",
	})
}

// Tiers, confirmed sponsors and the enquiry pipeline behind an event's Sponsorships tab.
export function useEventSponsorships(event: string) {
	return useCall<EventSponsorships, { event: string }>({
		url: "/api/v2/method/buzz.api.sponsorships.get_event_sponsorships",
		params: { event },
	})
}

// The sponsors list; search, filters and sort run on the server and refetch on change.
export function useEventSponsors(
	event: string,
	search: Ref<string>,
	order: Ref<ListOrder>,
	conditions: Ref<Condition[]>,
) {
	const debouncedSearch = refDebounced(search, 300)
	return useCall<EventSponsors, Record<string, string>>({
		url: "/api/v2/method/buzz.api.sponsorships.get_event_sponsors",
		params: () => ({
			event,
			search: debouncedSearch.value.trim(),
			filters: JSON.stringify(conditions.value),
			order: order.value,
		}),
		refetch: true,
	})
}

// One enquiry in full, fetched when its drawer opens.
export function useEnquiryDetail(enquiry: () => string | null) {
	return useCall<EnquiryDetail, { enquiry: string }>({
		url: "/api/v2/method/buzz.api.sponsorships.get_event_sponsorship_enquiry",
		params: () => ({ enquiry: enquiry() ?? "" }),
		immediate: false,
	})
}

export function useUpdateEnquiryStatus() {
	return useCall<string, { enquiry: string; status: string }>({
		url: "/api/v2/method/buzz.api.sponsorships.update_enquiry_status",
		method: "POST",
		immediate: false,
	})
}
