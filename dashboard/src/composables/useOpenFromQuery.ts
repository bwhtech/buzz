import { useRouteQuery } from "@vueuse/router"
import { watchEffect } from "vue"

/**
 * Opens the row a link names in `?<param>=<id>` once the list holding it has loaded,
 * then drops the parameter so a reload or a closed drawer does not open it again.
 */
export function useOpenFromQuery<T>(
	param: string,
	find: (id: string) => T | undefined,
	open: (item: T) => void,
) {
	const id = useRouteQuery<string | null>(param, null)

	watchEffect(() => {
		const item = id.value ? find(id.value) : undefined
		if (!item) return
		open(item)
		id.value = null
	})
}
