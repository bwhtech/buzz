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

/** `HH:mm` and `HH:mm:ss` both reach here; padded, they compare correctly as text. */
function normalizedTime(time: string): string {
	return time.length === 5 ? `${time}:00` : time
}

/**
 * Whether an event would end before — or exactly when — it starts.
 *
 * Only single-day events can fail this: a span that runs into another day may well end
 * earlier in the day than it began. An unset end date is a single day, which is what
 * `alignedEndDate` leaves behind. Mirrors `validate_dates` on Buzz Event, which is what
 * actually enforces it; this is only here so the form says so before the save does.
 *
 * A half-filled schedule is not an error yet — the organiser is still picking.
 */
export function isEndBeforeStart(
	startDate: string,
	endDate: string,
	startTime: string,
	endTime: string,
): boolean {
	if (!startTime || !endTime) return false
	if (endDate && endDate !== startDate) return false
	return normalizedTime(endTime) <= normalizedTime(startTime)
}
