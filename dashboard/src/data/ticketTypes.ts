import { useCall } from "frappe-ui"

import type { EventTicketTypes } from "@/types"

export function useEventTicketTypes(event: string) {
	return useCall<EventTicketTypes, { event: string }>({
		url: "/api/v2/method/buzz.api.events.get_event_ticket_types",
		params: { event },
	})
}

type TicketTypeAccessValues = { requires_approval: boolean; enable_waitlist: boolean }

export function useSetTicketTypeAccess() {
	const setter = useCall<null, TicketTypeAccessValues & { ticket_type: string }>({
		url: "/api/v2/method/buzz.api.events.set_ticket_type_access",
		method: "POST",
		immediate: false,
	})
	async function save(ticketType: string, values: TicketTypeAccessValues) {
		const { requires_approval, enable_waitlist } = values
		// submit() resolves on a server error too, so the error is read off the call.
		await setter
			.submit({ ticket_type: ticketType, requires_approval, enable_waitlist })
			.catch(() => null)
		if (setter.error) throw setter.error
	}
	return { save }
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
