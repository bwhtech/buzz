<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { ErrorMessage } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import { ListFilters } from "@/components/common/filters"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import TransactionDrawer from "@/components/dashboard/transactions/TransactionDrawer.vue"
import TransactionSummaryCards from "@/components/dashboard/transactions/TransactionSummaryCards.vue"
import TransactionTable from "@/components/dashboard/transactions/TransactionTable.vue"
import { useDeepLinkedRecord } from "@/composables/useDeepLinkedRecord"
import { useEventTransactions } from "@/composables/useEventTransactions"
import { useListQuery } from "@/composables/useListQuery"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError } from "@/types"

const eventId = useRoute().params.eventId as string

const { search, order, conditions, isFiltered } = useListQuery()

const { transactions, fetchOne, loadMore, page, loadingFirstPage, loadingMore } =
	useEventTransactions(eventId, search, order, conditions)

const message = (error: unknown) => (error as FrappeError | null)?.message

const { selectedId, selected } = useDeepLinkedRecord({
	param: "booking",
	rows: transactions,
	fetchOne,
	notFound: __("This transaction isn't available"),
})

const selectedIndex = computed(() =>
	transactions.value.findIndex((row) => row.name === selectedId.value),
)

const drawerOpen = computed<boolean>({
	get: () => selected.value !== null,
	set: (open) => !open && (selectedId.value = null),
})

const step = (by: number) => {
	const next = transactions.value[selectedIndex.value + by]
	if (next) selectedId.value = next.name
}

const sentinel = ref<HTMLElement | null>(null)
useIntersectionObserver(sentinel, ([entry]) => entry?.isIntersecting && loadMore(), {
	rootMargin: "400px",
})
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Transactions" />

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<ErrorMessage v-if="page.error && !page.data" :message="message(page.error)" />

		<template v-else>
			<TransactionSummaryCards :event="eventId" />

			<section class="space-y-3">
				<h2 class="text-lg font-semibold text-ink-gray-9">Transactions</h2>

				<ListFilters
					v-model="conditions"
					v-model:search="search"
					v-model:order="order"
					:fields="page.data?.filter_fields ?? []"
					search-placeholder="Search by booking, transaction ID, name or email"
				/>

				<p v-if="isFiltered" aria-live="polite" class="text-sm text-ink-gray-5">
					{{ page.data?.matched ?? 0 }} of {{ page.data?.total ?? 0 }} transactions
				</p>

				<TransactionTable
					v-if="loadingFirstPage"
					:transactions="[]"
					:selected-id="null"
					:loading-rows="6"
				/>

				<ErrorMessage v-else-if="page.error" :message="message(page.error)" />

				<TransactionTable
					v-else-if="transactions.length"
					:transactions="transactions"
					:selected-id="selectedId"
					:loading-rows="loadingMore ? 3 : 0"
					@open="selectedId = $event"
				/>

				<EmptyState
					v-else-if="isFiltered"
					title="No matching transactions"
					:description="
						search.trim()
							? `Nothing here matches “${search.trim()}”.`
							: 'Nothing here matches these filters.'
					"
					icon="lucide-filter-x"
				/>
				<EmptyState
					v-else
					title="No transactions yet"
					description="Paid bookings show up here once buyers check out."
					icon="lucide-arrow-left-right"
				/>

				<div ref="sentinel" aria-hidden="true" />
			</section>
		</template>
	</PageWithSidebar>

	<TransactionDrawer
		v-model:open="drawerOpen"
		:event="eventId"
		:booking="selected?.name ?? null"
		:has-previous="selectedIndex > 0"
		:has-next="selectedIndex >= 0 && selectedIndex < transactions.length - 1"
		@previous="step(-1)"
		@next="step(1)"
	/>
</template>
