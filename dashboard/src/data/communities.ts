import { useCall } from "frappe-ui"

import type { CommunityQueue } from "@/types"

const METHOD = "/api/v2/method/buzz.api.communities"

export function useCommunityQueue(community: string) {
	return useCall<CommunityQueue, { community: string }>({
		url: `${METHOD}.get_requests`,
		params: { community },
	})
}

// One per review action; each takes the request's name.
export function useReviewAction(action: "approve_request" | "reject_request" | "remove_event") {
	return useCall<null, { request: string }>({
		url: `${METHOD}.${action}`,
		method: "POST",
		immediate: false,
	})
}
