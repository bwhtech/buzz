import type { EventCollaborator, EventSection, SectionLevel } from "@/types"

export type SectionOption = { key: EventSection; label: string; description: string }

export const EVENT_SECTIONS: SectionOption[] = [
	{
		key: "details",
		label: "Details",
		description: "Event details and settings. Always at least view.",
	},
	{ key: "guests", label: "Guests", description: "Guest list, registrations and check-in." },
	{
		key: "ticketing",
		label: "Ticketing",
		description: "Ticket types, coupons and form questions.",
	},
	{ key: "talks", label: "Talks", description: "Talk proposals and schedule." },
	{
		key: "sponsors",
		label: "Sponsorships",
		description: "Sponsorship tiers, enquiries and sponsors.",
	},
	{ key: "communications", label: "Announcements", description: "Emails sent to guests." },
]

export const LEVEL_OPTIONS = [
	{ label: "No access", value: "" },
	{ label: "View", value: "View" },
	{ label: "Edit", value: "Edit" },
]

// Details cannot be switched off: every collaborator at least sees the event.
export const DETAILS_LEVEL_OPTIONS = LEVEL_OPTIONS.filter((option) => option.value)

export type SectionLevels = Record<`${EventSection}_access`, SectionLevel | "">

export function emptySectionLevels(): SectionLevels {
	return {
		details_access: "View",
		guests_access: "",
		ticketing_access: "",
		talks_access: "",
		sponsors_access: "",
		communications_access: "",
	}
}

export function levelsOf(collaborator: EventCollaborator): SectionLevels {
	const levels = emptySectionLevels()
	for (const key of Object.keys(levels) as (keyof SectionLevels)[]) {
		levels[key] = collaborator[key]
	}
	return levels
}

/** "View all" / "Edit all": the details level stays at least View, which both satisfy. */
export function setAllLevels(levels: SectionLevels, level: SectionLevel): void {
	for (const key of Object.keys(levels) as (keyof SectionLevels)[]) levels[key] = level
}

/** One line per granted section, for the collaborators table. */
export function describeLevels(levels: SectionLevels): string {
	return EVENT_SECTIONS.filter((section) => levels[`${section.key}_access`])
		.map((section) => `${section.label}: ${levels[`${section.key}_access`]}`)
		.join(", ")
}
