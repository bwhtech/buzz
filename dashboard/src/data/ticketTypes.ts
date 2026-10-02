import { useCall } from "frappe-ui"

import type { EventTicketTypes } from "@/types"

export function useEventTicketTypes(event: string) {
	return useCall<EventTicketTypes, { event: string }>({
		url: "/api/v2/method/buzz.api.events.get_event_ticket_types",
		params: { event },
	})
}
