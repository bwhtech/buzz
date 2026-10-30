import type { EventCollaborator, EventSection, SectionLevel } from "@/types"

export type SectionOption = {
	key: EventSection
	label: string
	description: string
	icon: string
}

export const EVENT_SECTIONS: SectionOption[] = [
	{
		key: "details",
		label: "Details",
		description: "Event details and settings. Always at least view.",
		icon: "lucide-file-text",
	},
	{
		key: "guests",
		label: "Guests",
		description: "Guest list, registrations and check-in.",
		icon: "lucide-users",
	},
	{
		key: "ticketing",
		label: "Ticketing",
		description: "Ticket types, coupons and form questions.",
		icon: "lucide-ticket",
	},
	{
		key: "talks",
		label: "Talks",
		description: "Talk proposals and schedule.",
		icon: "lucide-presentation",
	},
	{
		key: "sponsors",
		label: "Sponsorships",
		description: "Sponsorship tiers, enquiries and sponsors.",
		icon: "lucide-handshake",
	},
	{
		key: "communications",
		label: "Announcements",
		description: "Emails sent to guests.",
		icon: "lucide-megaphone",
	},
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

export function grantedSections(levels: SectionLevels) {
	return EVENT_SECTIONS.filter((section) => levels[`${section.key}_access`]).map((section) => ({
		...section,
		level: levels[`${section.key}_access`] as SectionLevel,
	}))
}

/** Section labels per level with access, Edit first. `null` labels means every section. */
export function describeLevels(levels: SectionLevels) {
	const granted = grantedSections(levels)
	return (["Edit", "View"] as const)
		.map((level) => {
			const labels = granted
				.filter((section) => section.level === level)
				.map((section) => section.label)
			return { level, labels: labels.length === EVENT_SECTIONS.length ? null : labels }
		})
		.filter((line) => line.labels?.length !== 0)
}

/** Details View alone opens no page in the dashboard, so the server refuses it. */
export function opensAPage(levels: SectionLevels): boolean {
	return levels.details_access === "Edit" || grantedSections(levels).length > 1
}
