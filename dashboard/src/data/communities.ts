import { useCall } from "frappe-ui"

import type { CommunityQueue } from "@/types"

export function useCommunityRequests(community: string) {
	return useCall<CommunityQueue, { community: string }>({
		url: "/api/v2/method/buzz.api.communities.get_requests",
		params: { community },
	})
}

export function useReviewRequest(decision: "approve" | "reject") {
	return useCall<null, { request: string }>({
		url: `/api/v2/method/buzz.api.communities.${decision}_request`,
		method: "POST",
		immediate: false,
	})
}
