import { useCall } from "frappe-ui"

import type { CommunityQueue, EventOption, EventRequests } from "@/types"

const API = "/api/v2/method/buzz.api.communities"

function postAction(method: string) {
	return useCall<unknown, Record<string, unknown>>({
		url: `${API}.${method}`,
		method: "POST",
		immediate: false,
	})
}

export function useEventRequests(event: string) {
	return useCall<EventRequests, { event: string }>({
		url: `${API}.get_event_requests`,
		params: { event },
	})
}

export function useCommunityQueue(community: string) {
	return useCall<CommunityQueue, { community: string }>({
		url: `${API}.get_requests`,
		params: { community },
	})
}

export function useAddableEvents(community: string, query: () => string) {
	return useCall<EventOption[], { community: string; txt: string }>({
		url: `${API}.search_addable_events`,
		params: () => ({ community, txt: query() }),
		refetch: true,
	})
}

export const submitEvent = postAction("submit_event")
export const withdrawRequest = postAction("withdraw_request")
export const resubmitRequest = postAction("resubmit_request")
export const approveRequest = postAction("approve_request")
export const rejectRequest = postAction("reject_request")
export const removeEvent = postAction("remove_event")
export const addEvent = postAction("add_event")
