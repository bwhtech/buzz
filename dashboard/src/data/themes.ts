import { useList } from "frappe-ui"

export function useEnabledThemes() {
	return useList<{ name: string }>({
		doctype: "Buzz Theme",
		fields: ["name"],
		filters: { enabled: 1 },
		orderBy: "creation asc",
		limit: 100,
	})
}
