/**
 * Comma-joined lists in a query string.
 *
 * Kept apart from the composable so the serialisation is testable on its own: anything
 * importing vue-router drags in the app, and node --test cannot load that.
 */

/** An absent, blank or all-blank param reads as no selection rather than one empty value. */
export function parseQueryList(raw: string | null | undefined): string[] {
	if (!raw) return []
	return raw
		.split(",")
		.map((value) => value.trim())
		.filter(Boolean)
}

/** Empty selections serialise to null so the caller can drop the param entirely. */
export function formatQueryList(values: string[]): string | null {
	const kept = values.map((value) => value.trim()).filter(Boolean)
	return kept.length ? kept.join(",") : null
}
