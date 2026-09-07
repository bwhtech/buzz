// Unsaved form edits, kept against the document they were typed on top of.

export interface StoredDraft<T> {
	/** The clean document the edits were made against. */
	baseline: T
	/** The form as it was last left. */
	form: T
}

/** What a stored draft turned out to be worth. */
export type DraftOutcome<T> =
	| { status: "restored"; form: T }
	/** Typed against an older copy of the document, so replaying it would undo the change. */
	| { status: "stale" }
	| { status: "none" }

/** Value equality for two snapshots of the same form shape. */
export function matches<T>(one: T, other: T): boolean {
	return JSON.stringify(one) === JSON.stringify(other)
}

/** Reads a stored draft against the document as it now stands. */
export function restoredDraft<T>(stored: Partial<StoredDraft<T>>, baseline: T): DraftOutcome<T> {
	const { baseline: typedAgainst, form } = stored
	if (!typedAgainst || !form) return { status: "none" }
	if (!matches(typedAgainst, baseline)) return { status: "stale" }
	return matches(form, baseline) ? { status: "none" } : { status: "restored", form }
}
