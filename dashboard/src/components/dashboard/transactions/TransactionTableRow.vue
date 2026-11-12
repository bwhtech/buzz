<script setup lang="ts">
import { Badge, Button, Tooltip, dayjsLocal } from "frappe-ui"

import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import type { TransactionRow } from "@/types"
import { formatCurrency } from "@/utils/currency"
import { paymentStatusTheme, refundStatusTheme, truncateMiddle } from "@/utils/transactionStatus"

defineProps<{ transaction: TransactionRow; selected?: boolean }>()

const emit = defineEmits<{ open: [] }>()

const copyToClipboard = useCopyToClipboard()
</script>

<template>
	<tr
		class="cursor-pointer text-base transition-colors duration-150 ease-out hover:bg-surface-gray-1 motion-reduce:transition-none"
		:class="selected && 'bg-surface-gray-2'"
		@click="emit('open')"
	>
		<td class="px-3 py-2">
			<button
				type="button"
				class="font-mono text-sm text-ink-gray-9 focus-visible:underline focus-visible:outline-none"
				:aria-label="`Open ${transaction.name}`"
				@click.stop="emit('open')"
			>
				{{ transaction.name }}
			</button>
		</td>
		<td class="whitespace-nowrap px-3 py-2 text-ink-gray-7">
			{{ dayjsLocal(transaction.created_at).format("D MMM YYYY, h:mm A") }}
		</td>
		<td class="max-w-56 px-3 py-2">
			<div class="truncate text-ink-gray-9">{{ transaction.buyer_name || "—" }}</div>
			<div class="truncate text-sm text-ink-gray-5">{{ transaction.buyer_email }}</div>
		</td>
		<td class="px-3 py-2 text-right tabular-nums text-ink-gray-7">{{ transaction.tickets }}</td>
		<td class="whitespace-nowrap px-3 py-2 text-right tabular-nums text-ink-gray-9">
			{{ formatCurrency(transaction.total_amount, transaction.currency ?? undefined) }}
		</td>
		<td class="whitespace-nowrap px-3 py-2 text-ink-gray-7">
			{{ transaction.payment_method || "—" }}
		</td>
		<td class="px-3 py-2">
			<Badge
				v-if="transaction.payment_status"
				variant="subtle"
				:theme="paymentStatusTheme(transaction.payment_status)"
				:label="transaction.payment_status"
			/>
		</td>
		<td class="px-3 py-2">
			<Badge
				v-if="transaction.refund_status"
				variant="subtle"
				:theme="refundStatusTheme(transaction.refund_status)"
				:label="transaction.refund_status"
			/>
		</td>
		<td class="whitespace-nowrap px-3 py-2">
			<span v-if="transaction.payment_id" class="flex items-center gap-1">
				<Tooltip :text="transaction.payment_id">
					<span class="font-mono text-sm text-ink-gray-7">
						{{ truncateMiddle(transaction.payment_id) }}
					</span>
				</Tooltip>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-copy"
					aria-label="Copy transaction ID"
					@click.stop="copyToClipboard(transaction.payment_id, 'Transaction ID copied')"
				/>
			</span>
			<span v-else class="text-ink-gray-5">—</span>
		</td>
	</tr>
</template>
