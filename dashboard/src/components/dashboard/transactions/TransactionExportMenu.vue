<script setup lang="ts">
import { Button, Dropdown, call, toast } from "frappe-ui"
import { computed, ref } from "vue"

import type { TransactionRow, TransactionsPage } from "@/types"
import { downloadCsv } from "@/utils/csv"

type ExportQuery = { search: string; filters: string; order: string; status?: string }

const props = defineProps<{
	event: string
	title?: string | null
	// What the list is currently showing, so the export is the same list.
	query: ExportQuery
	isFiltered: boolean
}>()

const ALL_TRANSACTIONS: ExportQuery = { search: "", filters: "[]", order: "desc" }

const exporting = ref<"shown" | "all" | null>(null)

async function fetchAll(query: ExportQuery): Promise<TransactionRow[]> {
	const all: TransactionRow[] = []
	for (let start = 0; ; start += 100) {
		const page: TransactionsPage = await call("buzz.api.transactions.get_event_transactions", {
			event: props.event,
			...query,
			start,
			limit: 100,
		})
		all.push(...page.transactions)
		if (!page.has_next_page) return all
	}
}

const csvRow = (row: TransactionRow) => [
	row.name,
	row.created_at,
	row.buyer_name,
	row.buyer_email,
	String(row.tickets),
	String(row.total_amount),
	row.currency,
	row.payment_method,
	row.payment_status,
	row.refund_status,
	row.payment_id,
]

async function exportTransactions(scope: "shown" | "all") {
	exporting.value = scope
	try {
		const rows = await fetchAll(scope === "all" ? ALL_TRANSACTIONS : props.query)
		downloadCsv(`${props.title || "Event"} transactions.csv`, [
			[
				"Booking ID",
				"Created at",
				"Buyer name",
				"Buyer email",
				"Tickets",
				"Amount",
				"Currency",
				"Payment method",
				"Payment status",
				"Refund status",
				"Payment ID",
			],
			...rows.map(csvRow),
		])
	} catch {
		toast.error("Could not export the transactions. Try again.")
	} finally {
		exporting.value = null
	}
}

const options = computed(() => [
	{ label: "Download CSV", icon: "lucide-download", onClick: () => exportTransactions("shown") },
	...(props.isFiltered
		? [
				{
					label: "Download all transactions",
					icon: "lucide-download",
					onClick: () => exportTransactions("all"),
				},
			]
		: []),
])
</script>

<template>
	<Dropdown :options="options" align="end">
		<Button :label="__('Export')" :loading="exporting !== null">
			<template #prefix>
				<span class="lucide-download size-4" aria-hidden="true" />
			</template>
		</Button>
	</Dropdown>
</template>
