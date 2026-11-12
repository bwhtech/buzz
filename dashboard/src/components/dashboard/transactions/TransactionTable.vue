<script setup lang="ts">
import { Skeleton } from "frappe-ui"

import TransactionTableRow from "@/components/dashboard/transactions/TransactionTableRow.vue"
import type { TransactionRow } from "@/types"

defineProps<{
	transactions: TransactionRow[]
	selectedId: string | null
	// Placeholder rows for a page on its way.
	loadingRows?: number
}>()

const emit = defineEmits<{ open: [name: string] }>()

const COLUMNS = [
	{ label: "Booking ID" },
	{ label: "Amount", numeric: true },
	{ label: "Status" },
	{ label: "Buyer" },
	{ label: "Payment ID" },
	{ label: "Date" },
]
</script>

<template>
	<div class="overflow-x-auto">
		<table class="w-full min-w-[48rem]">
			<thead class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
				<tr>
					<th
						v-for="column in COLUMNS"
						:key="column.label"
						scope="col"
						class="h-8 whitespace-nowrap px-3 font-normal"
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
				<tr v-for="row in loadingRows ?? 0" :key="`loading-${row}`" class="h-10">
					<td v-for="column in COLUMNS" :key="column.label" class="px-3">
						<Skeleton class="h-4 w-full rounded-4" />
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>
