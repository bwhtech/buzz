import { dayjsLocal } from "frappe-ui"

import type { TicketTypeItem } from "@/types"

const isSoldOut = (ticketType: TicketTypeItem) =>
	ticketType.max_tickets_available > 0 &&
	ticketType.tickets_sold >= ticketType.max_tickets_available

export function ticketTypeBadge(ticketType: TicketTypeItem) {
	if (!ticketType.is_published) return { label: "Disabled", theme: "gray" as const }
	if (isSoldOut(ticketType)) return { label: "Sold out", theme: "amber" as const }
	return ticketType.requires_approval
		? { label: "Requires approval", theme: "gray" as const }
		: null
}

export function salesLabel(ticketType: TicketTypeItem) {
	if (!ticketType.auto_unpublish_after) return "No end date"
	return `Sales end ${dayjsLocal(ticketType.auto_unpublish_after).format("D MMM YYYY")}`
}

// A ticket type without a seat count sells any number of tickets.
export function seatsLabel(ticketType: TicketTypeItem) {
	const seats = ticketType.max_tickets_available
	const sold = ticketType.tickets_sold.toLocaleString()
	if (!seats) return `Unlimited · ${sold} sold`
	return `${sold} of ${seats.toLocaleString()} sold`
}

export function soldPercent(ticketType: TicketTypeItem) {
	const seats = ticketType.max_tickets_available
	return seats ? (ticketType.tickets_sold / seats) * 100 : null
}
