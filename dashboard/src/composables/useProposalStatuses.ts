import { createListResource } from "frappe-ui"

// Frappe color name (Talk Proposal Status.color) -> frappe-ui Badge theme.
// frappe-ui's Badge only themes these five colors, so the doctype's color
// options are limited to match.
type BadgeTheme = "blue" | "red" | "green" | "gray" | "orange"

const COLOR_TO_THEME: Record<string, BadgeTheme> = {
	Gray: "gray",
	Green: "green",
	Blue: "blue",
	Orange: "orange",
	Red: "red",
}

// Theme for the default statuses, used until the list loads or when a status
// has no color set.
const FALLBACK_THEME: Record<string, BadgeTheme> = {
	Accepted: "green",
	Shortlisted: "blue",
	"Review Pending": "orange",
	Rejected: "red",
	Replied: "blue",
	Duplicate: "gray",
}

// Tailwind emits only the icon classes it can see, so no interpolated names.
const STATUS_ICONS: Record<string, string> = {
	"Review Pending": "lucide-clock",
	Shortlisted: "lucide-bookmark",
	Accepted: "lucide-circle-check",
	Rejected: "lucide-circle-x",
	Replied: "lucide-reply",
	Duplicate: "lucide-layers-2",
}

const FALLBACK_ICON = "lucide-squircle-dashed"

// Module-level so every caller shares one fetch of the status list.
const statuses = createListResource({
	doctype: "Talk Proposal Status",
	fields: ["name", "color"],
	order_by: "creation asc",
	auto: true,
})

export function useProposalStatuses() {
	const getStatusTheme = (status: string): BadgeTheme => {
		const row = statuses.data?.find(
			(item: { name: string; color?: string }) => item.name === status,
		)
		if (row?.color && COLOR_TO_THEME[row.color]) {
			return COLOR_TO_THEME[row.color]
		}
		return FALLBACK_THEME[status] ?? "gray"
	}

	const getStatusIcon = (status: string): string => STATUS_ICONS[status] ?? FALLBACK_ICON

	return { statuses, getStatusTheme, getStatusIcon }
}
