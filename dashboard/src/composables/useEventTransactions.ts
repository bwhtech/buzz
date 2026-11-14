import { refDebounced } from "@vueuse/core"
import { useRouteQuery } from "@vueuse/router"
import { useCall } from "frappe-ui"
import { computed, type Ref, watch } from "vue"

import type { Condition } from "@/components/common/filters"
import type { ListOrder } from "@/composables/useListQuery"
import type { TransactionsPage } from "@/types"

export const TRANSACTIONS_PAGE_SIZE = 25
const URL = "/api/v2/method/buzz.api.transactions.get_event_transactions"

/** One page of an event's transactions; the page number lives in `?page=`. */
export function useEventTransactions(
	event: string,
	search: Ref<string>,
	order: Ref<ListOrder>,
	conditions: Ref<Condition[]>,
	status: Ref<string | null>,
) {
	const debouncedSearch = refDebounced(search, 300)
	const pageParam = useRouteQuery<string | null>("page", null)
	const page = computed<number>({
		get: () => Math.max(1, Number(pageParam.value) || 1),
		set: (value) => (pageParam.value = value > 1 ? String(value) : null),
	})
	watch([debouncedSearch, order, conditions, status], () => (page.value = 1))

	// The list's search, filters, order and status, shared with the export.
	const query = computed(() => ({
		search: debouncedSearch.value.trim(),
		filters: JSON.stringify(conditions.value),
		order: order.value,
		...(status.value && { status: status.value }),
	}))

	const list = useCall<TransactionsPage, Record<string, string | number>>({
		url: URL,
		params: () => ({
			event,
			...query.value,
			start: (page.value - 1) * TRANSACTIONS_PAGE_SIZE,
			limit: TRANSACTIONS_PAGE_SIZE,
		}),
		refetch: true,
		// A page past the end, from an old link, falls back to the first.
		onSuccess: (data) => !data.transactions.length && page.value > 1 && (page.value = 1),
	})

	const lookup = useCall<TransactionsPage, Record<string, string | number>>({
		url: URL,
		immediate: false,
	})
	const fetchOne = async (name: string) =>
		(await lookup.submit({ event, name, limit: 1 }))?.transactions[0] ?? null

	return {
		list,
		query,
		page,
		transactions: computed(() => list.data?.transactions ?? []),
		fetchOne,
	}
}
