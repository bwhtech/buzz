// App-facing type hub. Domain entities re-export the generated DocType types in
// src/types/*; interfaces below cover shapes the dashboard sees that the stored
// schema does not describe (API-joined/computed fields and non-DocType data).

export type { BuzzEvent } from "@/types/Events/BuzzEvent"
export type { EventBooking } from "@/types/Ticketing/EventBooking"
export type { EventTicket } from "@/types/Ticketing/EventTicket"
export type { TicketAddOnValue } from "@/types/Ticketing/TicketAddOnValue"
export type { FrappeField } from "@/composables/useCustomFields"

import type { TicketAddOnValue } from "@/types/Ticketing/TicketAddOnValue"

// Errors rejected by frappe-ui resources carry server messages beyond Error.
export interface FrappeError extends Error {
	messages?: string[]
	exc?: string
	exc_type?: string
}

// Languages served by the translation API (not a Buzz DocType).
export interface Language {
	name: string
	language_name: string
	language_code: string
}

// A selectable option on an add-on, joined into ticket responses.
export interface TicketAddOnOption {
	name?: string
	title?: string
	value?: string
}

// Ticket add-on rows come back with the add-on definition joined on, so they
// carry title/options on top of the stored TicketAddOnValue fields.
export interface TicketAddOn extends TicketAddOnValue {
	title?: string
	user_selects_option?: 0 | 1 | boolean
	options?: TicketAddOnOption[]
}
