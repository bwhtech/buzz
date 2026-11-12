<script setup lang="ts">
import { Skeleton } from "frappe-ui"

import TransactionTableRow from "@/components/dashboard/transactions/TransactionTableRow.vue"
import type { TransactionRow } from "@/types"

defineProps<{
	transactions: TransactionRow[]
	selectedId: string | null
	// Placeholder rows drawn under the loaded ones, for a page on its way.
	loadingRows?: number
}>()

const emit = defineEmits<{ open: [name: string] }>()

const COLUMNS = [
	{ label: "Booking ID" },
	{ label: "Date" },
	{ label: "Buyer" },
	{ label: "Tickets", numeric: true },
	{ label: "Amount", numeric: true },
	{ label: "Payment method" },
	{ label: "Payment status" },
	{ label: "Refund status" },
	{ label: "Transaction ID" },
]
</script>

<template>
	<div class="overflow-x-auto rounded-5 border border-outline-gray-2">
		<table class="w-full">
			<thead class="bg-surface-gray-1 text-left text-sm text-ink-gray-5">
				<tr>
					<th
						v-for="column in COLUMNS"
						:key="column.label"
						scope="col"
						class="whitespace-nowrap px-3 py-2 font-medium"
						:class="column.numeric && 'text-right'"
					>
						{{ column.label }}
					</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-outline-gray-1">
				<TransactionTableRow
					v-for="transaction in transactions"
					:key="transaction.name"
					:transaction="transaction"
					:selected="transaction.name === selectedId"
					@open="emit('open', transaction.name)"
				/>
				<tr v-for="row in loadingRows ?? 0" :key="`loading-${row}`">
					<td v-for="column in COLUMNS" :key="column.label" class="px-3 py-3">
						<Skeleton class="h-4 w-full rounded-4" />
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>
