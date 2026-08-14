/**
 * The end date an event should carry once its start date changes.
 *
 * An unset end date follows the start, so a single-day event needs one pick rather than
 * two. An end date already past the start is left alone — a multi-day event keeps its
 * span when the organiser shifts the start within it. Only an end that has fallen
 * behind the start is pulled back into line.
 *
 * Dates are `YYYY-MM-DD`, which compares correctly as text.
 */
export function alignedEndDate(startDate: string, endDate: string): string {
	if (!startDate) return endDate
	return !endDate || endDate < startDate ? startDate : endDate
}
