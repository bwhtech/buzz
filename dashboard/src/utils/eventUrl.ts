/**
 * The public page for an event lives under /events/<route>.
 *
 * Built from the current origin rather than a configured base URL: the dashboard and the
 * bench answer on different ports in development, so anything hardcoded is wrong in one
 * of the two places.
 */
export function eventUrl(route: string): string {
	return `${window.location.origin}${eventPath(route)}`
}

/** The origin-relative path of an event's public page. */
export function eventPath(route: string): string {
	return `/events/${route}`
}

/**
 * Leaves the dashboard for the event's public page. A plain navigation, not a router
 * one: the page is served outside the SPA's /b base.
 */
export function openEventPage(route: string): void {
	window.open(eventUrl(route), "_blank", "noopener")
}

/** Puts an event's public link on the clipboard. Rejects if the browser refuses access. */
export async function copyEventUrl(route: string): Promise<void> {
	await navigator.clipboard.writeText(eventUrl(route))
}
