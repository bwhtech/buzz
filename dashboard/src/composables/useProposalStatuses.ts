import { createListResource } from "frappe-ui"

// Frappe color name (Talk Proposal Status.color) -> frappe-ui Badge theme.
// frappe-ui's Badge only themes these five colors, so the doctype's color
// options are limited to match.
type BadgeTheme = "blue" | "red" | "green" | "gray" | "amber"

const COLOR_TO_THEME: Record<string, BadgeTheme> = {
	Gray: "gray",
	Green: "green",
	Blue: "blue",
	Orange: "amber",
	Red: "red",
}

// Theme for the default statuses, used until the list loads or when a status
// has no color set.
const FALLBACK_THEME: Record<string, BadgeTheme> = {
	Accepted: "green",
	Shortlisted: "blue",
	"Review Pending": "amber",
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
	Withdrawn: "lucide-circle-slash",
}

const FALLBACK_ICON = "lucide-squircle-dashed"

// What the state means for the submitter. A status the site added itself gets the
// fallback: say nothing about a workflow we do not know.
const STATUS_MESSAGES: Record<string, string> = {
	"Review Pending":
		"Your proposal has been submitted and is under review. You can still edit it while it's pending.",
	Shortlisted: "Your proposal has been shortlisted and is under final consideration.",
	Accepted: "Congratulations! Your talk proposal has been accepted for the event.",
	Rejected:
		"Unfortunately, your proposal was not selected for this event. Thank you for your submission.",
	Replied: "Read their notes and reply if anything is still open.",
	Duplicate: "Another proposal for the same event already covers this talk.",
	Withdrawn: "You withdrew this proposal.",
}

const FALLBACK_MESSAGE = "The organisers set this status for your proposal."

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

	const getStatusMessage = (status: string): string => STATUS_MESSAGES[status] ?? FALLBACK_MESSAGE

	return { statuses, getStatusTheme, getStatusIcon, getStatusMessage }
}
