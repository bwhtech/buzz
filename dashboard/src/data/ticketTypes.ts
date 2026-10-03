import { useCall } from "frappe-ui"

import type { EventTicketTypes } from "@/types"

export function useEventTicketTypes(event: string) {
	return useCall<EventTicketTypes, { event: string }>({
		url: "/api/v2/method/buzz.api.events.get_event_ticket_types",
		params: { event },
	})
}

export interface TaxSettings {
	apply_tax: 0 | 1
	tax_inclusive: 0 | 1
	tax_label: string
	tax_percentage: number
}

export function useUpdateTaxSettings() {
	return useCall<unknown, { doctype: "Buzz Event"; name: string; fieldname: TaxSettings }>({
		url: "/api/v2/method/frappe.client.set_value",
		method: "POST",
		immediate: false,
	})
}
