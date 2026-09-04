// App-facing type hub. Domain entities re-export the generated DocType types in
// src/types/*; interfaces below cover shapes the dashboard sees that the stored
// schema does not describe (API-joined/computed fields and non-DocType data).

export type { BuzzEvent } from "@/types/Events/BuzzEvent"
export type { EventBooking } from "@/types/Ticketing/EventBooking"
export type { EventTicket } from "@/types/Ticketing/EventTicket"
export type { TicketAddOnValue } from "@/types/Ticketing/TicketAddOnValue"
export type { FrappeField } from "@/composables/useCustomFields"
export type { TalkProposal } from "@/types/Proposals/TalkProposal"

import type { FrappeField } from "@/composables/useCustomFields"
import type { EventTicket } from "@/types/Ticketing/EventTicket"
import type { TicketAddOnValue } from "@/types/Ticketing/TicketAddOnValue"

// A speaker listed on a proposal. Proposal Speaker holds contact details only —
// no photo, bio or Speaker Profile link until a proposal is accepted.
export interface ProposalSpeaker {
	first_name: string
	last_name: string | null
	email: string
}

// Rows from buzz.api.proposals.get_my_proposals: proposals where the session
// user is the submitter or a listed speaker, with the event columns joined on.
export interface ProposalListItem {
	name: string
	title: string
	event: string
	// Event columns come over a link hop, so a deleted event leaves them null.
	event_title: string | null
	start_date: string | null
	start_time: string | null
	end_date: string | null
	venue: string | null
	banner_image: string | null
	allow_editing_talks_after_acceptance: boolean
	status: string
	creation: string
	modified: string
	speakers: ProposalSpeaker[]
}

// buzz.api.proposals.get_event_proposals: one page of an event's own pipeline.
export interface EventProposals {
	title: string | null
	total: number
	matched: number
	proposals: ProposalListItem[]
	has_next_page: boolean
	// Read access alone is a Viewer or Frontdesk, who cannot change a status.
	can_write: boolean
}

// buzz.api.proposals.accept_proposal
export interface AcceptedProposal {
	proposal: string
	status: string
	talk: string
}

// buzz.api.proposals.get_event_proposal_trend
export interface DailySubmissions {
	date: string
	count: number
}

export interface StatusTotal {
	status: string
	count: number
}

export interface ProposalTrend {
	total: number
	per_day: DailySubmissions[]
	by_status: StatusTotal[]
}

// A proposal whose event row still resolves — the only kind the timeline can place.
export type ProposalWithEvent = ProposalListItem & { event_title: string; start_date: string }

// Errors rejected by frappe-ui resources carry server messages beyond Error.
export interface FrappeError extends Error {
	messages?: string[]
	exc?: string
	exc_type?: string
}

// buzz.api.account.get_user_info: every field but is_logged_in and brand_image
// is absent for guests, so the session fields stay optional.
export interface UserInfo {
	is_logged_in: boolean
	brand_image: string | null
	name?: string
	first_name?: string | null
	last_name?: string | null
	full_name?: string | null
	email?: string
	user_image?: string | null
	roles?: { role: string }[]
	language?: string | null
}

// Rows from buzz.api.teams.get_my_teams: the session user's enabled memberships
// with the team title and logo joined on.
export interface TeamOption {
	name: string
	team_name: string
	logo: string | null
	team_role: string
}

// buzz.api.events.get_my_events: events the user's teams host, plus events they
// hold a ticket to. is_host separates the two.
export interface MyEvent {
	name: string
	title: string
	route: string | null
	start_date: string
	end_date: string | null
	start_time: string | null
	end_time: string | null
	venue: string | null
	medium: string | null
	banner_image: string | null
	allow_editing_talks_after_acceptance: boolean
	is_host: boolean
	is_attendee: boolean
	team: string | null
	team_name: string | null
	team_logo: string | null
}

/** buzz.api.booking.get_booking_summary: one ticket type per line, add-ons beneath. */
export interface BookingLine {
	label: string
	quantity: number
	amount: number
	add_ons: BookingLine[]
}

export interface BookingSummary {
	name: string
	booked_by: string | null
	status: string
	payment_status: string
	payment_method: string | null
	is_offline: boolean
	currency: string
	booked_on: string
	lines: BookingLine[]
	net_amount: number
	discount_amount: number
	coupon_code: string | null
	tax_amount: number
	tax_label: string | null
	tax_percentage: number
	total_amount: number
}

export interface MyEvents {
	upcoming: MyEvent[]
	past: MyEvent[]
}

export interface GuestAddOn {
	title: string
	value: string | null
}

// buzz.api.events.get_event_guests: one row per submitted ticket, not per person.
export interface EventGuest {
	name: string
	attendee_name: string | null
	attendee_email: string | null
	ticket_type: string | null
	registered_at: string | null
	add_ons: GuestAddOn[]
}

// buzz.api.events.get_event_registration_trend
export interface DailyRegistrations {
	date: string
	ticket_type: string | null
	count: number
}

export interface TicketTypeTotal {
	ticket_type: string | null
	count: number
}

export interface RegistrationTrend {
	total: number
	per_day: DailyRegistrations[]
	by_ticket_type: TicketTypeTotal[]
}

export interface GuestTicketType {
	name: string
	title: string | null
}

export interface EventGuests {
	title: string | null
	start_date: string | null
	start_time: string | null
	end_date: string | null
	venue: string | null
	total: number
	matched: number
	registrations_closed: boolean
	guests: EventGuest[]
	ticket_types: GuestTicketType[]
	has_next_page: boolean
}

export interface EventVenueDetail {
	name: string
	address: string | null
}

// buzz.api.events.get_event: one event with everything its manage page edits.
export interface EventDetail {
	name: string
	title: string
	route: string | null
	team: string | null
	modified: string
	start_date: string
	end_date: string | null
	start_time: string | null
	end_time: string | null
	time_zone: string | null
	short_description: string | null
	about: string | null
	banner_image: string | null
	allow_editing_talks_after_acceptance: boolean
	medium: string | null
	venue: EventVenueDetail | null
	meeting_link: string | null
	is_published: boolean
}

// A ticket the user holds, flattened with the context its event carries.
export interface TicketStub {
	name: string
	attendee_name: string
	attendee_email: string | null
	ticket_type: string
	qr_code: string | null
	// A ticket issued outside a booking has none.
	booking: string | null
	// Event columns come over a link hop, so a deleted event leaves them null.
	event_title: string | null
	start_date: string | null
	start_time: string | null
	end_date: string | null
	venue: string | null
}

// A ticket whose event row still resolves — the only kind the ticket UI can draw.
export type TicketWithEvent = TicketStub & { event_title: string; start_date: string }

// buzz.api.tickets.get_ticket_details. doc, event and booking pass through as whole
// documents, so only the fields the drawer reads are typed.
export interface TicketDetails {
	doc: {
		name: string
		first_name: string | null
		last_name: string | null
		attendee_name: string
		attendee_email: string | null
		ticket_type: string
		qr_code: string | null
		booking: string | null
		creation: string
	}
	add_ons: TicketAddOnDetail[]
	event: { name: string; title: string; route: string | null; ticket_print_format: string | null }
	// Null for an attendee who did not pay for the ticket themselves.
	booking: {
		name: string
		user: string | null
		owner: string
		total_amount: number
		currency: string
	} | null
	ticket_type: { title: string }
}

export interface TicketAddOnDetail {
	id: string
	title: string | null
	value: string | null
	price: number | null
	currency: string | null
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
