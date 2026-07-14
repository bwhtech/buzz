import { useList } from "frappe-ui";

// Maps a Frappe color name (stored on the Talk Proposal Status doctype) to a
// frappe-ui Badge theme. Unknown colors fall back to "gray".
const COLOR_TO_THEME: Record<string, string> = {
	Gray: "gray",
	Green: "green",
	Blue: "blue",
	Orange: "orange",
	Red: "red",
	Yellow: "yellow",
	Purple: "purple",
	Pink: "pink",
	Cyan: "teal",
};

// Fallback theming for the seeded statuses so badges are colored even before
// the status list has loaded (or if a status has no color set).
const FALLBACK_THEME: Record<string, string> = {
	Accepted: "green",
	Shortlisted: "blue",
	"Review Pending": "orange",
	Rejected: "red",
};

export function useProposalStatuses() {
	const statuses = useList({
		doctype: "Talk Proposal Status",
		fields: ["name", "color"],
		orderBy: "creation asc",
		auto: true,
		cacheKey: "talk-proposal-statuses",
	});

	const getStatusTheme = (status: string): string => {
		const row = statuses.data?.find((item: { name: string }) => item.name === status);
		if (row?.color && COLOR_TO_THEME[row.color]) {
			return COLOR_TO_THEME[row.color];
		}
		return FALLBACK_THEME[status] ?? "gray";
	};

	return { statuses, getStatusTheme };
}
