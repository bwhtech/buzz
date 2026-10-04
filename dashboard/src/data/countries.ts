import { useList } from "frappe-ui"

// Every user reads the same list, so it is safe to persist.
export function useCountries() {
	return useList<{ name: string }>({
		doctype: "Country",
		fields: ["name"],
		orderBy: "name asc",
		limit: 0,
		cacheKey: "countries",
	})
}
