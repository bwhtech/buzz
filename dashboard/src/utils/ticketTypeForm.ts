import type { TicketTypeItem, TierPrice } from "@/types"

export type TicketTypeValues = {
	title: string
	description: string
	category: string
	is_hidden: boolean
	prices: TierPrice[]
	max_tickets_available: number
	requires_approval: boolean
	enable_waitlist: boolean
	auto_unpublish_after: string | null
}

export function blankTicketTypeValues(category: string, currency: string): TicketTypeValues {
	return {
		title: "",
		description: "",
		category,
		is_hidden: false,
		prices: [{ currency, price: 0 }],
		max_tickets_available: 0,
		requires_approval: false,
		enable_waitlist: false,
		auto_unpublish_after: null,
	}
}

export function ticketTypeValuesOf(ticketType: TicketTypeItem): TicketTypeValues {
	return {
		title: ticketType.title,
		description: ticketType.description ?? "",
		category: ticketType.category ?? "",
		is_hidden: ticketType.is_hidden,
		prices: ticketType.prices.map(({ currency, price }) => ({ currency, price })),
		max_tickets_available: ticketType.max_tickets_available,
		requires_approval: ticketType.requires_approval,
		enable_waitlist: ticketType.enable_waitlist,
		auto_unpublish_after: ticketType.auto_unpublish_after,
	}
}

/** Why the ticket type can't be saved yet, or null when it can. */
export function ticketTypeError(values: TicketTypeValues) {
	if (!values.title?.trim()) return "Enter a name."
	if (values.prices?.some((row) => !row.currency || !(row.price >= 0)))
		return "Give every price a currency and an amount of zero or more."
	return null
}

/** The values as the doctype stores them. */
export function ticketTypeDocValues(values: TicketTypeValues) {
	// Approval and waitlist save apart, through set_ticket_type_access: they can change the event.
	const { requires_approval: _approval, enable_waitlist: _waitlist, ...rest } = values
	return {
		...rest,
		is_hidden: (values.is_hidden ? 1 : 0) as 0 | 1,
		title: values.title.trim(),
		description: values.description.trim(),
	}
}
