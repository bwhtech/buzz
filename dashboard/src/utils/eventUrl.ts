/**
 * The public page for an event lives at the site root under the event's own route.
 *
 * Built from the current origin rather than a configured base URL: the dashboard and the
 * bench answer on different ports in development, so anything hardcoded is wrong in one
 * of the two places.
 */
export function eventUrl(route: string): string {
	return `${window.location.origin}/${route}`
}

/** Puts an event's public link on the clipboard. Rejects if the browser refuses access. */
export async function copyEventUrl(route: string): Promise<void> {
	await navigator.clipboard.writeText(eventUrl(route))
}
