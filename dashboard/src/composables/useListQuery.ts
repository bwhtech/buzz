import { useRouteQuery } from "@vueuse/router"
import { computed } from "vue"

import type { Condition } from "@/components/common/filters"

export type ListOrder = "asc" | "desc"

/**
 * A list's search, sort and filters, held in the query string so a filtered list survives
 * a reload and can be pasted to someone else. `useRouteQuery` writes with `router.replace`,
 * so editing them does not pile up history entries. Defaults drop their param.
 */
export function useListQuery() {
	const searchParam = useRouteQuery<string | null>("q", null)
	const orderParam = useRouteQuery<string | null>("order", null)
	const filtersParam = useRouteQuery<string | null>("filters", null)

	const search = computed<string>({
		get: () => searchParam.value ?? "",
		set: (term) => (searchParam.value = term.trim() ? term : null),
	})
	const order = computed<ListOrder>({
		get: () => (orderParam.value === "asc" ? "asc" : "desc"),
		set: (next) => (orderParam.value = next === "asc" ? "asc" : null),
	})
	// Filters travel as the same JSON the server reads.
	const conditions = computed<Condition[]>({
		get: () => parseConditions(filtersParam.value),
		set: (next) => (filtersParam.value = next.length ? JSON.stringify(next) : null),
	})
	const filtering = computed(() => Boolean(search.value.trim() || conditions.value.length))

	return { search, order, conditions, filtering }
}

// A hand-edited or truncated link shows the unfiltered list rather than breaking the page.
function parseConditions(raw: string | null): Condition[] {
	try {
		const parsed = JSON.parse(raw ?? "[]")
		return Array.isArray(parsed) ? parsed : []
	} catch {
		return []
	}
}
