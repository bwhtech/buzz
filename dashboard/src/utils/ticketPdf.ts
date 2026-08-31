/**
 * The printable ticket, straight off Frappe's own print-format download.
 *
 * The event picks the format; "Standard Ticket" is what the ticket email attaches when it
 * does not. Same origin as the API, so the session cookie carries the permission check.
 */
export function ticketPdfUrl(ticketId: string, printFormat?: string | null): string {
	const params = new URLSearchParams({
		doctype: "Event Ticket",
		name: ticketId,
		format: printFormat || "Standard Ticket",
	})
	return `/api/method/frappe.utils.print_format.download_pdf?${params}`
}
