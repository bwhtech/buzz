export type ManagerNavItem = {
	label: string
	shortLabel?: string
	icon: string
	to: string
	startsGroup?: boolean
}

// /events is a site page outside the dashboard router, so it opens as a full page load.
export const discoverEvents = {
	label: "Discover Events",
	shortLabel: "Discover",
	icon: "lucide-compass",
	href: "/events",
}

export const openDiscoverEvents = () => window.location.assign(discoverEvents.href)

export type Workspace = {
	title: string
	subtitle: string
	back: { label: string; to: string }
	icon?: string
	image?: string | null
}

type NavigationContext = {
	eventId?: string
	teamId?: string
	creatingEvent: boolean
	hasSponsorships: boolean
}

function rootItems(hasSponsorships: boolean): ManagerNavItem[] {
	const items: ManagerNavItem[] = [
		{ label: "Events", icon: "lucide-calendar-days", to: "/manage/events" },
		{
			label: "Talk Proposals",
			shortLabel: "Proposals",
			icon: "lucide-mic",
			to: "/manage/proposals",
		},
	]
	// Hidden until the user has an inquiry, the same rule the account page applies.
	if (hasSponsorships) {
		items.push({ label: "Sponsorship", icon: "lucide-handshake", to: "/manage/sponsorship" })
	}
	items.push({
		label: "Communities",
		icon: "lucide-users-round",
		to: "/manage/communities",
		startsGroup: true,
	})
	return items
}

function eventItems(eventId: string): ManagerNavItem[] {
	const event = `/manage/events/${eventId}`
	return [
		{ label: "Details", icon: "lucide-receipt-text", to: `${event}/details` },
		{ label: "Registration", icon: "lucide-ticket", to: `${event}/registrations` },
		{ label: "Guests", icon: "lucide-users-round", to: `${event}/guests` },
		{ label: "Talks", icon: "lucide-presentation", to: `${event}/talks` },
		{
			label: "Announcements",
			shortLabel: "Announce",
			icon: "lucide-megaphone",
			to: `${event}/communications`,
		},
		{
			label: "Sponsorships",
			shortLabel: "Sponsors",
			icon: "lucide-handshake",
			to: `${event}/sponsorships`,
		},
		{ label: "More", icon: "lucide-ellipsis", to: `${event}/more` },
	]
}

function teamItems(teamId: string): ManagerNavItem[] {
	const team = `/manage/communities/${teamId}`
	return [
		{ label: "Calendar", icon: "lucide-calendar-days", to: `${team}/events` },
		{ label: "Members", icon: "lucide-users-round", to: `${team}/members` },
		{ label: "Payments", icon: "lucide-credit-card", to: `${team}/payments` },
		// Settings stays the last item, whatever is added above it.
		{ label: "Settings", icon: "lucide-settings", to: `${team}/settings` },
	]
}

export function managerNavigation(context: NavigationContext): ManagerNavItem[] {
	// Creating an event is a page of its own; the shell holds only the way out of it.
	if (context.creatingEvent) return []
	if (context.eventId) return eventItems(context.eventId)
	if (context.teamId) return teamItems(context.teamId)
	return rootItems(context.hasSponsorships)
}
