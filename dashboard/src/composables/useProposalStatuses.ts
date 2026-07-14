import { createListResource } from "frappe-ui";

// Frappe color name (Talk Proposal Status.color) -> frappe-ui Badge theme.
const COLOR_TO_THEME: Record<string, string> = {
	Gray: "gray",
	Green: "green",
	Blue: "blue",
	Orange: "orange",
	Red: "red",
	Yellow: "yellow",
	Purple: "purple",
	Pink: "pink",
};

// Theme for the default statuses, used until the list loads or when a status
// has no color set.
const FALLBACK_THEME: Record<string, string> = {
	Accepted: "green",
	Shortlisted: "blue",
	"Review Pending": "orange",
	Rejected: "red",
};

// Module-level so every caller shares one fetch of the status list.
const statuses = createListResource({
	doctype: "Talk Proposal Status",
	fields: ["name", "color"],
	order_by: "creation asc",
	auto: true,
});

export function useProposalStatuses() {
	const getStatusTheme = (status: string): string => {
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
