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

/** A plain navigation, not a router one: the page is served outside the SPA's /b base. */
export function openTeamPage(slug: string): void {
	window.open(teamUrl(slug), "_blank", "noopener")
}
