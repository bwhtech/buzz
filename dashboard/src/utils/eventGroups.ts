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
 * `dateOf` picks the day an event is filed under; it defaults to its start date.
 */
export function groupEventsByMonth<T extends { start_date: string }>(
	events: T[],
	dateOf: (event: T) => string = (event) => event.start_date,
): MonthGroup<T>[] {
	const months = new Map<string, Map<string, T[]>>()

	for (const event of events) {
		const date = dateOf(event)
		const days = months.get(date.slice(0, 7)) || new Map<string, T[]>()
		months.set(date.slice(0, 7), days)
		days.set(date, [...(days.get(date) || []), event])
	}

	return [...months].map(([month, days]) => ({
		month,
		days: [...days].map(([date, dayEvents]) => ({ date, events: dayEvents })),
	}))
}
