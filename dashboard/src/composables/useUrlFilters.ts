import { useRouteQuery } from "@vueuse/router"
import { computed } from "vue"

import type { FilterValues } from "@/components/common/filters"
import { formatQueryList, parseQueryList } from "@/utils/queryList"

/**
 * Filter selections held in the query string, so a filtered list survives a reload and can
 * be pasted to someone else.
 *
 * One comma-joined param per group. Clearing a group drops its param rather than leaving
 * `?team=`, so the unfiltered view keeps a clean URL.
 *
 * `useRouteQuery` writes with `router.replace`, so toggling filters does not pile up history
 * entries — the Back button leaves the page rather than rewinding chips one at a time.
 */
export function useUrlFilters(keys: readonly string[]) {
	const params = keys.map((key) => [key, useRouteQuery<string | null>(key, null)] as const)

	return computed<FilterValues>({
		get: () => Object.fromEntries(params.map(([key, param]) => [key, parseQueryList(param.value)])),
		set: (next) => {
			for (const [key, param] of params) param.value = formatQueryList(next[key] || [])
		},
	})
}
