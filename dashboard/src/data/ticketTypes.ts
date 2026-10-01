import { useCall } from "frappe-ui"

import type { EventTicketTypes, TicketTypeInput } from "@/types"

export function useEventTicketTypes(event: string) {
	return useCall<EventTicketTypes, { event: string }>({
		url: "/api/v2/method/buzz.api.events.get_event_ticket_types",
		params: { event },
	})
}

export function useSaveEventTicketTypes() {
	return useCall<EventTicketTypes, { event: string; ticket_types: TicketTypeInput[] }>({
		url: "/api/v2/method/buzz.api.events.save_event_ticket_types",
		method: "POST",
		immediate: false,
	})
}
