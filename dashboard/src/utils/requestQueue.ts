import type { EventTicketTypes, RegistrationRequest, RequestType } from "@/types"

export type RequestSort = "newest" | "oldest" | "name"

export const ticketTypeOf = (row: RegistrationRequest) => row.attendees[0]?.ticket_type ?? ""

export const requesterName = (row: RegistrationRequest) =>
	row.buyer_name || row.attendees[0]?.full_name || row.buyer_email || "Unnamed guest"

export const firstName = (row: RegistrationRequest) => requesterName(row).split(" ")[0]

export const isPaid = (row: RegistrationRequest) => row.total_amount > 0

export function matchesSearch(row: RegistrationRequest, query: string): boolean {
	const needle = query.trim().toLowerCase()
	if (!needle) return true
	return `${requesterName(row)} ${row.buyer_email ?? ""}`.toLowerCase().includes(needle)
}

/** An empty ticket type means every ticket type. */
export const matchesTicketType = (row: RegistrationRequest, ticketType: string) =>
	!ticketType || ticketTypeOf(row) === ticketType

/** Whether the event routes registrations into this queue, by event flag or ticket type. */
export function isQueueEnabled(type: RequestType, settings: EventTicketTypes): boolean {
	if (type === "Approval")
		return (
			settings.requires_approval || settings.ticket_types.some((item) => item.requires_approval)
		)
	return (
		settings.enable_waitlist ||
		settings.ticket_types.some((item) => item.enable_waitlist && item.max_tickets_available > 0)
	)
}

const byName = (a: RegistrationRequest, b: RegistrationRequest) =>
	requesterName(a).localeCompare(requesterName(b))

const SORTERS: Record<RequestSort, (a: RegistrationRequest, b: RegistrationRequest) => number> = {
	newest: (a, b) => b.requested_at.localeCompare(a.requested_at),
	oldest: (a, b) => a.requested_at.localeCompare(b.requested_at),
	name: byName,
}

export const sortRequests = (rows: RegistrationRequest[], sort: RequestSort) =>
	rows.toSorted(SORTERS[sort])

/** The next people in line for a ticket type, as many as there are seats. */
export function nextInLine(rows: RegistrationRequest[], ticketType: string, seats: number) {
	return rows
		.filter((row) => row.position !== null && ticketTypeOf(row) === ticketType)
		.toSorted((a, b) => (a.position ?? 0) - (b.position ?? 0))
		.slice(0, Math.max(seats, 0))
}

/** Seats that can go to someone waiting right now, per ticket type. */
export function freedSeats(seatsFree: Record<string, number>, rows: RegistrationRequest[]) {
	return Object.entries(seatsFree)
		.map(([ticketType, seats]) => ({ ticketType, people: nextInLine(rows, ticketType, seats) }))
		.filter((entry) => entry.people.length)
}

/** "5m", "3h", "2d": how long ago, short enough for a row. */
export function shortAge(minutes: number): string {
	if (minutes < 60) return `${Math.max(1, Math.round(minutes))}m`
	if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h`
	return `${Math.round(minutes / (60 * 24))}d`
}
