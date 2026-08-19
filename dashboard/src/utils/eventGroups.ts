interface DayGroup<T> {
	date: string
	events: T[]
}

export interface MonthGroup<T> {
	month: string
	days: DayGroup<T>[]
}

/**
 * Groups a sorted list of events by month, then by day. Insertion order is kept,
 * so the caller's sort survives — ascending for upcoming, descending for past.
 */
export function groupEventsByMonth<T extends { start_date: string }>(
	events: T[]
): MonthGroup<T>[] {
	const months = new Map<string, Map<string, T[]>>()

	for (const event of events) {
		const month = event.start_date.slice(0, 7)
		const days = months.get(month) || new Map<string, T[]>()
		months.set(month, days)
		days.set(event.start_date, [...(days.get(event.start_date) || []), event])
	}

	return [...months].map(([month, days]) => ({
		month,
		days: [...days].map(([date, dayEvents]) => ({ date, events: dayEvents })),
	}))
}
