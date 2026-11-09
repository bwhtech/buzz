import { useCall } from "frappe-ui"

import type { RegistrationRequest } from "@/types"

const METHOD = "/api/v2/method/buzz.api.booking.requests"

export function useRegistrationRequests(event: string) {
	return useCall<RegistrationRequest[], { event: string }>({
		url: `${METHOD}.get_requests`,
		params: { event },
	})
}

export function useApproveRequest() {
	return useCall<null, { booking: string }>({
		url: `${METHOD}.approve_request`,
		method: "POST",
		immediate: false,
	})
}

export function useDeclineRequest() {
	return useCall<null, { booking: string; message?: string }>({
		url: `${METHOD}.decline_request`,
		method: "POST",
		immediate: false,
	})
}
