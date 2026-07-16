// Shared domain types mirroring the Buzz DocTypes as the dashboard consumes
// them. API responses add computed/joined fields on top of the stored schema,
// so each interface keeps an index signature for those extras while typing the
// fields the dashboard actually reads.

export interface CustomField {
	fieldname: string
	fieldtype: string
	label?: string
	options?: string
	reqd?: boolean | 0 | 1
	default?: string
	[key: string]: any
}

export interface Language {
	name: string
	language_name: string
	language_code: string
}

export interface AddOn {
	name?: string
	title?: string
	price?: number
	options?: AddOnOption[]
	[key: string]: any
}

export interface AddOnOption {
	name?: string
	title?: string
	[key: string]: any
}

export interface BuzzEvent {
	name?: string
	title: string
	route?: string
	start_date?: string
	start_time?: string
	end_date?: string
	end_time?: string
	venue?: string
	is_published?: boolean | 0 | 1
	// Computed by the API when listing events.
	starts_at?: string
	ends_at?: string
	[key: string]: any
}

export interface EventTicket {
	name?: string
	attendee_name?: string
	attendee_email?: string
	ticket_type?: string
	event?: string
	booking?: string
	qr_code?: string
	add_ons?: AddOn[]
	[key: string]: any
}

export interface EventBooking {
	name?: string
	event?: string
	user?: string
	total_amount?: number
	net_amount?: number
	currency?: string
	payment_status?: string
	status?: string
	tax_percentage?: number
	tax_label?: string
	tax_amount?: number
	[key: string]: any
}
