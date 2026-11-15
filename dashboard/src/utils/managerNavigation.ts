import type { AccessSection, EventAccess } from "@/types"

export type ManagerNavItem = {
	label: string
	shortLabel?: string
	icon: string
	to: string
	startsGroup?: boolean
	// The sidebar section heading this item sits under.
	group?: string
	// The event section that gates this item, and the level it needs.
	section?: AccessSection
	needs?: "Edit"
	// A count beside the label, and a dot when it needs attention.
	count?: number
	dot?: boolean
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
	// The user's level per section of the open event; without it every item shows.
	access?: EventAccess | null
	requestCounts?: { pending: number; waiting: number } | null
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

function eventItems(
	eventId: string,
	access?: EventAccess | null,
	counts?: NavigationContext["requestCounts"],
): ManagerNavItem[] {
	const event = `/manage/events/${eventId}`
	const items: ManagerNavItem[] = [
		// View opens the details page with its fields locked.
		{ label: "Details", icon: "lucide-receipt-text", to: `${event}/details`, section: "details" },
		{
			label: "Registration",
			icon: "lucide-ticket",
			to: `${event}/registrations`,
			section: "ticketing",
			group: "Ticketing",
		},
		{
			label: "Payments",
			icon: "lucide-credit-card",
			to: `${event}/payments`,
			section: "ticketing",
			group: "Ticketing",
		},
		{
			label: "Transactions",
			icon: "lucide-arrow-left-right",
			to: `${event}/transactions`,
			section: "transactions",
			group: "Ticketing",
		},
		{
			label: "Coupons",
			icon: "lucide-ticket-percent",
			to: `${event}/coupons`,
			section: "ticketing",
			group: "Ticketing",
		},
		{
			label: "Guests",
			icon: "lucide-users-round",
			to: `${event}/guests`,
			section: "guests",
			group: "Attendees",
		},
		{
			label: "Approvals",
			icon: "lucide-user-check",
			to: `${event}/approvals`,
			section: "guests",
			group: "Attendees",
			needs: "Edit",
			count: counts?.pending || undefined,
			dot: Boolean(counts?.pending),
		},
		{
			label: "Waitlist",
			icon: "lucide-list-ordered",
			to: `${event}/waitlist`,
			section: "guests",
			group: "Attendees",
			needs: "Edit",
			count: counts?.waiting || undefined,
		},
		// The check-in page is full screen, outside the manager shell.
		{
			label: "Check In",
			icon: "lucide-scan-line",
			to: `/check-in/${eventId}`,
			section: "guests",
			group: "Attendees",
			needs: "Edit",
		},
		{
			label: "Talks",
			icon: "lucide-presentation",
			to: `${event}/talks`,
			section: "talks",
			group: "Program",
		},
		{
			label: "Schedule",
			icon: "lucide-calendar-days",
			to: `${event}/schedule`,
			section: "talks",
			group: "Program",
		},
		{
			label: "Announcements",
			icon: "lucide-megaphone",
			to: `${event}/communications`,
			section: "communications",
			group: "Outreach",
		},
		{
			label: "Sponsorships",
			icon: "lucide-handshake",
			to: `${event}/sponsorships`,
			section: "sponsors",
			group: "Outreach",
		},
		{
			label: "Settings",
			icon: "lucide-settings",
			to: `${event}/settings`,
			section: "details",
			needs: "Edit",
		},
	]
	return access ? items.filter((item) => isAllowed(item, access)) : items
}

function isAllowed(item: ManagerNavItem, access: EventAccess): boolean {
	const level = item.section && access[item.section]
	return Boolean(level) && (!item.needs || level === item.needs)
}

/** Where an event opens: its first destination the user may use. */
export function firstEventPath(eventId: string, access: EventAccess): string | undefined {
	return eventItems(eventId, access)[0]?.to
}

function teamItems(teamId: string): ManagerNavItem[] {
	const team = `/manage/communities/${teamId}`
	return [
		{ label: "Calendar", icon: "lucide-calendar-days", to: `${team}/calendar` },
		{ label: "Members", icon: "lucide-users-round", to: `${team}/members` },
		{ label: "Payments", icon: "lucide-credit-card", to: `${team}/payments` },
		// Settings stays the last item, whatever is added above it.
		{ label: "Settings", icon: "lucide-settings", to: `${team}/settings` },
	]
}

export type ManagerNavGroup = { label?: string; items: ManagerNavItem[] }

/** Runs of adjacent items that share a heading; ungrouped items form unlabelled runs. */
export function navigationGroups(items: ManagerNavItem[]): ManagerNavGroup[] {
	const groups: ManagerNavGroup[] = []
	for (const item of items) {
		const last = groups.at(-1)
		if (last && last.label === item.group) last.items.push(item)
		else groups.push({ label: item.group, items: [item] })
	}
	return groups
}

export function managerNavigation(context: NavigationContext): ManagerNavItem[] {
	// Creating an event is a page of its own; the shell holds only the way out of it.
	if (context.creatingEvent) return []
	if (context.eventId) return eventItems(context.eventId, context.access, context.requestCounts)
	if (context.teamId) return teamItems(context.teamId)
	return rootItems(context.hasSponsorships)
}
