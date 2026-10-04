import { useRouteQuery } from "@vueuse/router"
import { computed } from "vue"

import type { Condition } from "@/components/common/filters"

/**
 * List filters held in `?filters=` as the same JSON the server reads, so a filtered list
 * survives a reload and can be pasted to someone else. Written with `router.replace`, so
 * editing a filter does not pile up history entries.
 */
export function useUrlConditions() {
	const param = useRouteQuery<string | null>("filters", null)

	return computed<Condition[]>({
		get: () => parse(param.value),
		set: (next) => (param.value = next.length ? JSON.stringify(next) : null),
	})
}

// A hand-edited or truncated link shows the unfiltered list rather than breaking the page.
function parse(raw: string | null): Condition[] {
	try {
		const parsed = JSON.parse(raw ?? "[]")
		return Array.isArray(parsed) ? parsed : []
	} catch {
		return []
	}
}
