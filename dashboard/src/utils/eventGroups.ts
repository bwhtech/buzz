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
 * Events without a date close the list as one group with an empty month and date.
 */
export function groupEventsByMonth<T extends { start_date: string | null }>(
	events: T[],
	dateOf: (event: T) => string | null = (event) => event.start_date,
): MonthGroup<T>[] {
	const months = new Map<string, Map<string, T[]>>()
	const undated: T[] = []

	for (const event of events) {
		const date = dateOf(event)
		if (!date) {
			undated.push(event)
			continue
		}
		const days = months.get(date.slice(0, 7)) || new Map<string, T[]>()
		months.set(date.slice(0, 7), days)
		days.set(date, [...(days.get(date) || []), event])
	}

	const groups = [...months].map(([month, days]) => ({
		month,
		days: [...days].map(([date, dayEvents]) => ({ date, events: dayEvents })),
	}))
	if (undated.length) groups.push({ month: "", days: [{ date: "", events: undated }] })
	return groups
}
