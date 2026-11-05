import { watch } from "vue"
import { useRoute, useRouter } from "vue-router"

/**
 * `?<param>=<name>` opens that row once the page's rows arrive, then leaves the URL.
 * For pages that load every row at once; paged lists use useDeepLinkedRecord.
 */
export function useQueryParamRecord<T extends { name: string }>(
	param: string,
	rows: () => T[] | undefined,
	open: (row: T) => void,
) {
	const route = useRoute()
	const router = useRouter()

	watch(
		[() => route.query[param], rows],
		([name, list]) => {
			if (typeof name !== "string" || !name || !list) return
			const row = list.find((option) => option.name === name)
			if (row) open(row)
			router.replace({ query: { ...route.query, [param]: undefined } })
		},
		{ immediate: true },
	)
}
