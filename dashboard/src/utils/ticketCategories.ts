import type { AvailableTicketType, BookingTicketCategory } from "@/types"

export type TicketTypeGroup = {
	category: BookingTicketCategory | null
	ticketTypes: AvailableTicketType[]
}

// The server sends ticket types in category order, uncategorized last.
export function groupTicketTypes(
	ticketTypes: AvailableTicketType[],
	categories: BookingTicketCategory[],
): TicketTypeGroup[] {
	const groups = categories.map((category) => ({
		category,
		ticketTypes: ticketTypes.filter((ticketType) => ticketType.category === category.name),
	}))
	const uncategorized = ticketTypes.filter(
		(ticketType) => !categories.some((category) => category.name === ticketType.category),
	)
	return uncategorized.length ? [...groups, { category: null, ticketTypes: uncategorized }] : groups
}
