import { useCall } from "frappe-ui"

import type { EventRequests } from "@/types"

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

export const submitEvent = postAction("submit_event")
export const withdrawRequest = postAction("withdraw_request")
export const resubmitRequest = postAction("resubmit_request")
