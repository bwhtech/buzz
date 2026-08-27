import { useList } from "frappe-ui"

import { session } from "@/data/session"
import { userResource } from "@/data/user"
import type { TicketStub } from "@/types"

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
