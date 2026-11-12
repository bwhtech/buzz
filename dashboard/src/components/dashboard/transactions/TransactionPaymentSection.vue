<script setup lang="ts">
import { Badge, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import DetailRow from "@/components/common/DetailRow.vue"
import CopyableDetailRow from "@/components/dashboard/transactions/CopyableDetailRow.vue"
import TransactionSection from "@/components/dashboard/transactions/TransactionSection.vue"
import type { TransactionDetail } from "@/types"

const props = defineProps<{ transaction: TransactionDetail }>()

const formatDate = (date: string) => dayjsLocal(date).format("D MMM YYYY, h:mm A")

const multiplePayments = computed(() => props.transaction.payments.length > 1)
const pending = computed(() => props.transaction.payment_status === "Verification Pending")
</script>

<template>
	<TransactionSection title="Payment">
		<div
			v-for="(payment, index) in transaction.payments"
			:key="payment.name"
			class="space-y-3"
			:class="multiplePayments && 'rounded-4 border border-outline-gray-2 p-3'"
		>
			<p v-if="multiplePayments" class="text-sm font-medium text-ink-gray-5">
				Payment {{ index + 1 }}
			</p>
			<dl class="space-y-3 text-base">
				<DetailRow label="Method" :value="payment.payment_gateway" />
				<CopyableDetailRow label="Payment ID" :value="payment.payment_id" />
				<CopyableDetailRow label="Order ID" :value="payment.order_id" />
				<DetailRow label="Status">
					<Badge
						variant="subtle"
						:theme="payment.payment_received ? 'green' : 'amber'"
						:label="payment.payment_received ? 'Received' : 'Not received'"
					/>
				</DetailRow>
				<DetailRow label="Paid at" :value="formatDate(payment.created_at)" />
			</dl>
		</div>
		<dl v-if="!transaction.payments.length" class="space-y-3 text-base">
			<DetailRow
				label="Method"
				:value="transaction.offline_payment_method || transaction.payment_method"
			/>
			<DetailRow label="Status">
				<Badge
					variant="subtle"
					:theme="pending ? 'amber' : 'green'"
					:label="pending ? 'Awaiting verification' : 'Received'"
				/>
			</DetailRow>
		</dl>
	</TransactionSection>
</template>
