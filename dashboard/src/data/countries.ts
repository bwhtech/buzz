import { useList } from "frappe-ui"

// Every user reads the same list, so it is safe to persist.
// useList treats limit 0 as unset and falls back to 20, so ask for more than the ~250 countries.
export function useCountries() {
	return useList<{ name: string }>({
		doctype: "Country",
		fields: ["name"],
		orderBy: "name asc",
		limit: 1000,
		cacheKey: "countries",
	})
}
