import { useCall } from "frappe-ui"

const METHOD = "/api/v2/method/buzz.api.communities"

// One per review action; each takes the request's name.
export function useReviewAction(action: "approve_request" | "reject_request") {
	return useCall<null, { request: string }>({
		url: `${METHOD}.${action}`,
		method: "POST",
		immediate: false,
	})
}
