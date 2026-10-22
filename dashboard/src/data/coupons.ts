import { useCall } from "frappe-ui"

import type { EventCoupons } from "@/types"

export function useEventCoupons(event: string) {
	return useCall<EventCoupons, { event: string }>({
		url: "/api/v2/method/buzz.api.events.get_event_coupons",
		params: { event },
	})
}
