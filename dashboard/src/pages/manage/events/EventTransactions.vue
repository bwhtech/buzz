<script setup lang="ts">
import { useRouteQuery } from "@vueuse/router"
import { ErrorMessage, TabButtons } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import { ListFilters } from "@/components/common/filters"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import DevDataToggle from "@/components/dashboard/transactions/DevDataToggle.vue"
import TransactionDrawer from "@/components/dashboard/transactions/TransactionDrawer.vue"
import TransactionExportMenu from "@/components/dashboard/transactions/TransactionExportMenu.vue"
import TransactionPagination from "@/components/dashboard/transactions/TransactionPagination.vue"
import TransactionSummaryCards from "@/components/dashboard/transactions/TransactionSummaryCards.vue"
import TransactionTable from "@/components/dashboard/transactions/TransactionTable.vue"
import { useDeepLinkedRecord } from "@/composables/useDeepLinkedRecord"
import { TRANSACTIONS_PAGE_SIZE, useEventTransactions } from "@/composables/useEventTransactions"
import { useListQuery } from "@/composables/useListQuery"
import { useEventAccess } from "@/data/events"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import { serverErrorMessage } from "@/utils/serverError"

const isDev = import.meta.env.DEV

const eventId = useRoute().params.eventId as string

const { search, order, conditions, isFiltered: isNarrowed } = useListQuery()

const STATUS_TABS = [
	{ label: "All", value: "all" },
	{ label: "Paid", value: "paid" },
	{ label: "Pending verification", value: "pending" },
	{ label: "Refunded", value: "refunded" },
]
const statusParam = useRouteQuery<string | null>("status", null)
const status = computed<string>({
	get: () => statusParam.value ?? "all",
	set: (value) => (statusParam.value = value === "all" ? null : value),
})
const isFiltered = computed(() => isNarrowed.value || Boolean(statusParam.value))

const { list, page, transactions, fetchOne } = useEventTransactions(
	eventId,
	search,
	order,
	conditions,
	statusParam,
)

const exportQuery = computed(() => ({
	search: search.value.trim(),
	filters: JSON.stringify(conditions.value),
	order: order.value,
	status: statusParam.value ?? "",
}))

const access = useEventAccess(() => eventId)
access.fetch()

const message = serverErrorMessage

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
</script>

<template>
	<EventPageHeader :title="list.data?.title" section="Transactions" />

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<ErrorMessage v-if="list.error && !list.data" :message="message(list.error)" />

		<template v-else>
			<TransactionSummaryCards :event="eventId" @review-pending="status = 'pending'" />

			<section class="space-y-3">
				<div class="flex items-center justify-between gap-3">
					<h2 class="text-lg font-semibold text-ink-gray-9">Transactions</h2>
					<TransactionExportMenu
						v-if="list.data?.total"
						:event="eventId"
						:title="list.data.title"
						:query="exportQuery"
						:is-filtered="isFiltered"
					/>
				</div>

				<TabButtons v-model="status" :options="STATUS_TABS" />

				<ListFilters
					v-model="conditions"
					v-model:search="search"
					v-model:order="order"
					:fields="list.data?.filter_fields ?? []"
					search-placeholder="Search transactions"
				/>

				<TransactionTable
					v-if="list.loading && !list.data"
					:transactions="[]"
					:selected-id="null"
					:loading-rows="6"
				/>

				<ErrorMessage v-else-if="list.error" :message="message(list.error)" />

				<template v-else-if="transactions.length">
					<TransactionTable
						:transactions="transactions"
						:selected-id="selectedId"
						@open="selectedId = $event"
					/>
					<TransactionPagination
						v-model:page="page"
						:total="list.data?.matched ?? 0"
						:page-size="TRANSACTIONS_PAGE_SIZE"
					/>
				</template>

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
			</section>
		</template>
	</PageWithSidebar>

	<DevDataToggle v-if="isDev" />

	<TransactionDrawer
		v-model:open="drawerOpen"
		:event="eventId"
		:booking="selected?.name ?? null"
		:has-previous="selectedIndex > 0"
		:has-next="selectedIndex >= 0 && selectedIndex < transactions.length - 1"
		:can-download-invoice="Boolean(access.data?.guests)"
		@previous="step(-1)"
		@next="step(1)"
	/>
</template>
