import { useCall } from "frappe-ui"

import type { EventTicketTypes } from "@/types"

export function useEventTicketTypes(event: string) {
	return useCall<EventTicketTypes, { event: string }>({
		url: "/api/v2/method/buzz.api.events.get_event_ticket_types",
		params: { event },
	})
}

export interface TaxSettings {
	apply_tax: boolean
	tax_inclusive: boolean
	tax_label: string
	tax_percentage: number
}

export function useUpdateTaxSettings() {
	return useCall<null, TaxSettings & { event: string }>({
		url: "/api/v2/method/buzz.api.events.update_tax_settings",
		method: "POST",
		immediate: false,
	})
}

export interface TeamTaxDetails {
	legal_name: string
	tax_id: string
	billing_address: string
}

export function useUpdateTeamTaxDetails() {
	return useCall<null, TeamTaxDetails & { event: string }>({
		url: "/api/v2/method/buzz.api.events.update_team_tax_details",
		method: "POST",
		immediate: false,
	})
}
