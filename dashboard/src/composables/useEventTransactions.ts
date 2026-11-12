import { refDebounced } from "@vueuse/core"
import { useCall } from "frappe-ui"
import { computed, type Ref, ref, watch } from "vue"

import type { Condition } from "@/components/common/filters"
import type { ListOrder } from "@/composables/useListQuery"
import type { TransactionRow, TransactionsPage } from "@/types"

const PAGE_SIZE = 20
const URL = "/api/v2/method/buzz.api.transactions.get_event_transactions"

/** One event's transactions, a page at a time, the way useEventGuests walks the guest list. */
export function useEventTransactions(
	event: string,
	search: Ref<string>,
	order: Ref<ListOrder>,
	conditions: Ref<Condition[]>,
) {
	const debouncedSearch = refDebounced(search, 300)
	const start = ref(0)
	const transactions = ref<TransactionRow[]>([])

	const page = useCall<TransactionsPage, Record<string, string | number>>({
		url: URL,
		params: () => ({
			event,
			search: debouncedSearch.value.trim(),
			filters: JSON.stringify(conditions.value),
			order: order.value,
			start: start.value,
			limit: PAGE_SIZE,
		}),
		refetch: true,
		onSuccess: (data) => {
			if (start.value === 0) {
				transactions.value = data.transactions
				return
			}
			const seen = new Set(transactions.value.map((row) => row.name))
			transactions.value = [
				...transactions.value,
				...data.transactions.filter((row) => !seen.has(row.name)),
			]
		},
	})

	const lookup = useCall<TransactionsPage, Record<string, string | number>>({
		url: URL,
		immediate: false,
	})
	const fetchOne = async (name: string) =>
		(await lookup.submit({ event, name, limit: 1 }))?.transactions[0] ?? null

	watch([debouncedSearch, order, conditions], () => (start.value = 0), { flush: "sync" })

	const loadMore = () => {
		if (page.loading || !page.data?.has_next_page) return
		start.value += PAGE_SIZE
	}

	return {
		transactions,
		fetchOne,
		loadMore,
		page,
		loadingFirstPage: computed(() => page.loading && start.value === 0),
		loadingMore: computed(() => page.loading && start.value > 0),
	}
}
