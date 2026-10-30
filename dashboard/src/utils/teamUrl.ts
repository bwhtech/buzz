/**
 * The public page for a team lives under /community/<slug>.
 *
 * Built from the current origin, as eventUrl is: the dashboard and the bench answer on
 * different ports in development, so the server's own URL is wrong in one of the two.
 */
export function teamPath(slug: string): string {
	return `/community/${slug}`
}

export function teamUrl(slug: string): string {
	return `${window.location.origin}${teamPath(slug)}`
}

/** A personal calendar's public page: its owner's profile. */
export function profileUrl(username: string): string {
	return `${window.location.origin}/u/${username}`
}
