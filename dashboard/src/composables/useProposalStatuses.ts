import { createListResource } from "frappe-ui";

// Frappe color name (Talk Proposal Status.color) -> frappe-ui Badge theme.
// frappe-ui's Badge only themes these five colors, so the doctype's color
// options are limited to match.
type BadgeTheme = "blue" | "red" | "green" | "gray" | "orange";

const COLOR_TO_THEME: Record<string, BadgeTheme> = {
	Gray: "gray",
	Green: "green",
	Blue: "blue",
	Orange: "orange",
	Red: "red",
};

// Theme for the default statuses, used until the list loads or when a status
// has no color set.
const FALLBACK_THEME: Record<string, BadgeTheme> = {
	Accepted: "green",
	Shortlisted: "blue",
	"Review Pending": "orange",
	Rejected: "red",
	Replied: "blue",
	Duplicate: "gray",
};

// Module-level so every caller shares one fetch of the status list.
const statuses = createListResource({
	doctype: "Talk Proposal Status",
	fields: ["name", "color"],
	order_by: "creation asc",
	auto: true,
});

export function useProposalStatuses() {
	const getStatusTheme = (status: string): BadgeTheme => {
		const row = statuses.data?.find(
			(item: { name: string; color?: string }) => item.name === status,
		);
		if (row?.color && COLOR_TO_THEME[row.color]) {
			return COLOR_TO_THEME[row.color];
		}
		return FALLBACK_THEME[status] ?? "gray";
	};

	return { statuses, getStatusTheme };
}
