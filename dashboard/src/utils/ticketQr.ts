/**
 * Pull a ticket ID out of a scanned QR payload, which may be the bare ID or a ticket URL.
 * Returns null when nothing ticket-shaped is found.
 */
export function extractTicketId(qrData: string): string | null {
	// If QR contains just the ticket ID
	if (qrData.match(/^[A-Z0-9-]+$/)) {
		return qrData
	}

	// If QR contains a URL with ticket ID
	const urlMatch = qrData.match(/ticket[/=]([A-Z0-9-]+)/i)
	if (urlMatch) {
		return urlMatch[1]
	}

	// Try to extract any alphanumeric string that looks like a ticket ID
	const idMatch = qrData.match(/([A-Z0-9-]{10,})/i)
	if (idMatch) {
		return idMatch[1]
	}

	return null
}
