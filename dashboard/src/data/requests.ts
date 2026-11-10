import { call, useCall } from "frappe-ui"
import { ref, watch } from "vue"

import type { RegistrationRequest, RequestCounts, RequestType } from "@/types"
import type { RequestAction } from "@/utils/requestStatus"

const METHOD = "buzz.api.booking.requests"

export function useRegistrationRequests(event: string, requestType: RequestType) {
	return useCall<RegistrationRequest[], { event: string; request_type: RequestType }>({
		url: `/api/v2/method/${METHOD}.get_requests`,
		params: { event, request_type: requestType },
	})
}

// Bumped after every write, so the sidebar badge and the page cards recount together.
const countsVersion = ref(0)

export const refreshRequestCounts = () => countsVersion.value++

export function useRequestCounts(event: () => string) {
	const counts = useCall<RequestCounts, { event: string }>({
		url: `/api/v2/method/${METHOD}.get_request_counts`,
		params: () => ({ event: event() }),
		immediate: false,
	})
	watch([event, countsVersion], ([name]) => name && counts.reload(), { immediate: true })
	return counts
}

const ENDPOINTS: Record<RequestAction, string[]> = {
	approve: ["approve_request"],
	// A declined request is reopened before it can be approved.
	approve_anyway: ["reopen_request", "approve_request"],
	decline: ["decline_request"],
	reopen: ["reopen_request"],
	revoke: ["revoke_request"],
	resend: ["resend_payment_link"],
}

export async function runRequestAction(action: RequestAction, booking: string) {
	try {
		for (const endpoint of ENDPOINTS[action]) await call(`${METHOD}.${endpoint}`, { booking })
	} finally {
		refreshRequestCounts()
	}
}
