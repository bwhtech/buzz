import { session } from "@/data/session"
import { userResource } from "@/data/user"
import type { TicketStub, TicketType } from "@/types"
import { useList } from "frappe-ui"

// Everything the printed ticket shows lives on the ticket or one link hop away,
// so the standard list call covers it without a whitelisted endpoint.
export function useMyTickets() {
	return useList<TicketStub>({
		doctype: "Event Ticket",
		fields: [
			"name",
			"attendee_name",
			"qr_code",
			"ticket_type.title as ticket_type",
			"event.title as event_title",
			"event.start_date",
			"event.end_date",
			"event.start_time",
			"event.venue",
		],
		// Tickets are held by email address, which is the session id for everyone
		// except Administrator — hence the account email first.
		filters: () => ({
			attendee_email: userResource.data?.email || session.user,
			docstatus: 1,
		}),
		// No cacheKey: it persists to IndexedDB and would outlive this user's session.
		orderBy: "creation desc",
	})
}

/**
 * The tiers an event sells, oldest first.
 *
 * Plain doctype reads and writes, so no endpoint of its own: Event Ticket Type inherits
 * its event's team scope from the permission hooks, and the filter below only narrows
 * what the page asks for. `tickets_sold` and `remaining_tickets` are Python properties
 * rather than columns, so a list call cannot carry them.
 */
export function useEventTicketTypes(event: string) {
	return useList<TicketType>({
		doctype: "Event Ticket Type",
		fields: ["name", "title", "price", "currency", "is_published", "max_tickets_available"],
		filters: { event },
		orderBy: "creation asc",
		limit: 0,
	})
}

/** Currencies a tier can be priced in. Readable by everyone, so nothing scopes this. */
export function useCurrencies() {
	return useList<{ name: string }>({
		doctype: "Currency",
		fields: ["name"],
		filters: { enabled: 1 },
		orderBy: "name asc",
		limit: 0,
		cacheKey: "currencies",
	})
}
