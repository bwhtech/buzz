<script setup lang="ts">
import { Badge, dayjsLocal } from "frappe-ui"

import CopyableDetailRow from "@/components/dashboard/transactions/CopyableDetailRow.vue"
import TransactionSection from "@/components/dashboard/transactions/TransactionSection.vue"
import type { TransactionDetail } from "@/types"
import { formatCurrency } from "@/utils/currency"
import { pluralize } from "@/utils/pluralize"

const props = defineProps<{ transaction: TransactionDetail }>()

const money = (amount: number) => formatCurrency(amount, props.transaction.currency ?? undefined)
</script>

<template>
	<TransactionSection title="Refunds">
		<div
			v-for="refund in transaction.refunds"
			:key="refund.name"
			class="space-y-3 rounded-4 border border-outline-gray-2 p-3 text-base"
		>
			<div class="flex items-center gap-2">
				<span class="font-medium tabular-nums text-ink-gray-9">{{ money(refund.amount) }}</span>
				<Badge v-if="refund.status" variant="subtle" :label="refund.status" />
				<span class="ml-auto text-sm text-ink-gray-5">
					{{ dayjsLocal(refund.created_at).format("D MMM YYYY") }}
				</span>
			</div>
			<p v-if="refund.tickets.length" class="text-sm text-ink-gray-5">
				{{ pluralize(refund.tickets.length, "ticket") }}: {{ refund.tickets.join(", ") }}
			</p>
			<dl>
				<CopyableDetailRow label="Refund ID" :value="refund.refund_id" />
			</dl>
		</div>
	</TransactionSection>
</template>
