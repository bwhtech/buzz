// Decorative barcode: bar and gap widths come from the ticket id's characters, so a
// ticket always draws the same strip. Not scannable — the QR code carries the data.

const BAR = "var(--ink-gray-8)"

/** `angle` turns the strip: the default draws bars across, "180deg" draws them down. */
export function barcodePattern(ticketId: string, angle = "90deg"): string {
	if (!ticketId) return "none"
	const stops: string[] = []
	let edge = 0
	for (const character of ticketId) {
		const code = character.charCodeAt(0)
		const width = 1 + (code % 3)
		const gap = 1 + ((code >> 2) % 3)
		stops.push(
			`${BAR} ${edge}px ${edge + width}px`,
			`transparent ${edge + width}px ${edge + width + gap}px`,
		)
		edge += width + gap
	}
	return `linear-gradient(${angle}, ${stops.join(", ")})`
}
