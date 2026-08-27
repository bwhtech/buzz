export type TimelineTab = "upcoming" | "past"

interface Dated {
	start_date: string
	end_date?: string | null
}

/**
 * Splits dated rows into the tab they belong to, sorted the way that tab reads:
 * upcoming counts from today forwards, past counts backwards from yesterday.
 * A row running through today is not over yet, so end_date decides where it falls.
 */
export function inTab<T extends Dated>(items: T[], tab: TimelineTab, today: string): T[] {
	const upcoming = tab === "upcoming"
	const isOver = (item: T) => (item.end_date || item.start_date) < today

	return (
		items
			.filter((item) => isOver(item) !== upcoming)
			// oxlint-disable-next-line no-array-sort -- sorts the array .filter() just created
			.sort((a, b) => (upcoming ? 1 : -1) * a.start_date.localeCompare(b.start_date))
	)
}
