<script setup lang="ts">
import { Badge, dayjsLocal } from "frappe-ui"

import DetailRow from "@/components/common/DetailRow.vue"
import CopyableDetailRow from "@/components/dashboard/transactions/CopyableDetailRow.vue"
import TransactionSection from "@/components/dashboard/transactions/TransactionSection.vue"
import type { TransactionDetail } from "@/types"
import { formatCurrency } from "@/utils/currency"

defineProps<{ transaction: TransactionDetail }>()

const formatDate = (date: string) => dayjsLocal(date).format("D MMM YYYY, h:mm A")
</script>

<template>
	<TransactionSection title="Payment">
		<dl class="space-y-3 text-base">
			<DetailRow label="Method" :value="transaction.payment_method" />
			<DetailRow
				v-if="transaction.offline_payment_method"
				label="Offline"
				:value="transaction.offline_payment_method"
			/>
		</dl>

		<dl
			v-for="payment in transaction.payments"
			:key="payment.name"
			class="space-y-3 rounded-4 border border-outline-gray-2 p-3 text-base"
		>
			<DetailRow label="Gateway" :value="payment.payment_gateway">
				<template #suffix>
					<Badge
						variant="subtle"
						:theme="payment.payment_received ? 'green' : 'amber'"
						:label="payment.payment_received ? 'Received' : 'Not received'"
					/>
				</template>
			</DetailRow>
			<DetailRow
				label="Amount"
				:value="formatCurrency(payment.amount, payment.currency ?? undefined)"
			/>
			<CopyableDetailRow label="Transaction ID" :value="payment.payment_id" />
			<CopyableDetailRow label="Order ID" :value="payment.order_id" />
			<DetailRow label="Paid at" :value="formatDate(payment.created_at)" />
		</dl>
	</TransactionSection>
</template>
