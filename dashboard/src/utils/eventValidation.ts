import { isEndBeforeStart } from "./eventDates.ts"

export interface EventDraft {
	title: string
	startDate: string
	startTime: string
	endDate: string
	endTime: string
}

export interface ChecklistItem {
	label: string
	done: boolean
	/** Element id the save handler focuses when this is what is missing. */
	field: string
}

/**
 * What an event needs before it can be created, and what the draft already has.
 *
 * Shown as a live checklist rather than enforced by a disabled button, so the organiser
 * can see which field is holding the save back. Only the name is required: the date and
 * the venue can be announced later.
 */
export function eventDraftChecklist(draft: EventDraft): ChecklistItem[] {
	const endsBeforeItStarts = isEndBeforeStart(
		draft.startDate,
		draft.endDate,
		draft.startTime,
		draft.endTime,
	)
	return [
		{ label: "Name", done: Boolean(draft.title.trim()), field: "event-title" },
		// A schedule nobody has filled in yet cannot run backwards, so this only earns a row
		// once it can actually fail.
		...(endsBeforeItStarts
			? [{ label: "Ends after it starts", done: false, field: "event-schedule-end" }]
			: []),
	]
}

export function isDraftComplete(draft: EventDraft): boolean {
	return eventDraftChecklist(draft).every((item) => item.done)
}
