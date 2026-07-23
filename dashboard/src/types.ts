// App-facing type hub. Domain entities re-export the generated DocType types in
// src/types/*; interfaces below cover shapes the dashboard sees that the stored
// schema does not describe (API-joined/computed fields and non-DocType data).

export type { BuzzEvent } from "@/types/Events/BuzzEvent"
export type { EventBooking } from "@/types/Ticketing/EventBooking"
export type { EventTicket } from "@/types/Ticketing/EventTicket"
export type { TicketAddOnValue } from "@/types/Ticketing/TicketAddOnValue"
export type { FrappeField } from "@/composables/useCustomFields"

import type { FrappeField } from "@/composables/useCustomFields"
import type { EventTicket } from "@/types/Ticketing/EventTicket"
import type { TicketAddOnValue } from "@/types/Ticketing/TicketAddOnValue"

// Rows from buzz.api.proposals.get_my_proposals: proposals where the session
// user is the submitter or a listed speaker, with the event title joined on.
export interface ProposalListItem {
	name: string
	title: string
	event: string
	event_title: string | null
	status: string
	creation: string
}

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

// Ticket add-on rows come back with the add-on definition joined on, so they
// carry an id, title and selectable options on top of the stored fields.
export interface TicketAddOn extends TicketAddOnValue {
	id?: string
	title?: string
	user_selects_option?: 0 | 1 | boolean
	options?: string[]
}

// Tickets rendered in the dashboard carry the joined add-on rows.
export interface DashboardTicket extends EventTicket {
	add_ons?: TicketAddOn[]
}

// Booking-form view models (shapes assembled client-side, not stored DocTypes).

export interface AvailableTicketType {
	name: string | number
	event?: string
	title?: string
	price?: number
	currency?: string
	description?: string
	remaining_tickets?: number
	free_add_ons?: string[]
	add_ons?: string[]
}

export interface AvailableAddOn {
	name: string
	title?: string
	description?: string
	price?: number
	currency?: string
	options?: string[]
	user_selects_option?: 0 | 1 | boolean
}

export interface AttendeeAddOnSelection {
	selected: boolean
	option: string | null
}

export interface BookingAttendee {
	id: number
	first_name: string
	last_name: string
	email: string
	ticket_type?: string
	add_ons?: Record<string, AttendeeAddOnSelection>
	custom_fields?: Record<string, any>
	[key: string]: any
}

export interface OfflineMethod {
	name?: string
	title: string
	description?: string
	collect_payment_proof?: 0 | 1 | boolean
	custom_fields?: FrappeField[]
}

export interface CouponData {
	id?: string
	title?: string
	description?: string
	coupon_type?: string
	discount_type?: string
	discount_value?: number
	max_discount_amount?: number
	min_order_value?: number
	free_add_ons?: string[]
	ticket_type?: string
	remaining_tickets?: number
	[key: string]: any
}
