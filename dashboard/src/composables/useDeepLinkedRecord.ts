import { toast } from "frappe-ui"
import { computed, type Ref, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

type Row = { name: string }

/**
 * The record a list page has open in its drawer, which a `?<param>=<name>` link can open.
 *
 * A linked record past the loaded pages is fetched through `fetchOne`, the list's own
 * permission-checked endpoint. The param leaves the URL once read, so closing the drawer
 * does not bring it back.
 */
export function useDeepLinkedRecord<T extends Row>(options: {
	param: string
	rows: Ref<T[]>
	fetchOne: (name: string) => Promise<T | null>
	notFound: string
}) {
	const route = useRoute()
	const router = useRouter()
	const selectedId = ref<string | null>(null)
	const fetched = ref<T | null>(null) as Ref<T | null>
	// The watcher can still fire for the route being navigated to, before this page unmounts.
	const pageRoute = route.name

	watch(
		() => route.query[options.param],
		(name) => {
			if (typeof name !== "string" || !name || route.name !== pageRoute) return
			selectedId.value = name
			router.replace({ query: { ...route.query, [options.param]: undefined } })
		},
		{ immediate: true },
	)

	watch(
		selectedId,
		async (name) => {
			fetched.value = null
			if (!name || options.rows.value.some((row) => row.name === name)) return
			const row = await options.fetchOne(name).catch(() => null)
			if (selectedId.value !== name) return
			if (row) fetched.value = row
			else {
				toast.error(options.notFound)
				selectedId.value = null
			}
		},
		{ immediate: true },
	)

	const selected = computed(
		() =>
			options.rows.value.find((row) => row.name === selectedId.value) ??
			(fetched.value?.name === selectedId.value ? fetched.value : null),
	)

	return { selectedId, selected }
}
