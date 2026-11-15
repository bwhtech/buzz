import type { TransactionLineItem } from "../types.ts"

export type BreakdownLine = {
	key: string
	label: string
	count: number
	unitPrice: number
	addOn: boolean
}

function countBy<T>(items: T[], keyOf: (item: T) => string, lineOf: (item: T) => BreakdownLine) {
	const lines = new Map<string, BreakdownLine>()
	for (const item of items) {
		const key = keyOf(item)
		const line = lines.get(key)
		if (line) line.count += 1
		else lines.set(key, { ...lineOf(item), key })
	}
	return [...lines.values()]
}

/** Tickets of one type and price read as one line with a count; add-ons follow, counted the same way. */
export function breakdownLines(items: TransactionLineItem[]): BreakdownLine[] {
	const tickets = countBy(
		items,
		(item) => `ticket:${item.ticket_type}:${item.amount}`,
		(item) => ({
			key: "",
			label: item.ticket_type || "Ticket",
			count: 1,
			unitPrice: item.amount,
			addOn: false,
		}),
	)
	const addOns = countBy(
		items.flatMap((item) => item.add_on_items ?? []),
		(addOn) => `add-on:${addOn.title}:${addOn.price}`,
		(addOn) => ({ key: "", label: addOn.title, count: 1, unitPrice: addOn.price, addOn: true }),
	)
	return [...tickets, ...addOns]
}
