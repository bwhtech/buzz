export type ManagerNavItem = {
	label: string
	shortLabel?: string
	icon: string
	to: string
}

type NavigationContext = {
	eventId?: string
	creatingEvent: boolean
	hasSponsorships: boolean
}

function rootItems(hasSponsorships: boolean): ManagerNavItem[] {
	const items = [
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
	return items
}

function eventItems(eventId: string): ManagerNavItem[] {
	const event = `/manage/events/${eventId}`
	return [
		{ label: "Details", icon: "lucide-receipt-text", to: `${event}/details` },
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

export function managerNavigation(context: NavigationContext): ManagerNavItem[] {
	// Creating an event is a page of its own; the shell holds only the way out of it.
	if (context.creatingEvent) return []
	if (context.eventId) return eventItems(context.eventId)
	return rootItems(context.hasSponsorships)
}
