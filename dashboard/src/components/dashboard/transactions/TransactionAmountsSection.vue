<script setup lang="ts">
import { computed } from "vue"

import TransactionSection from "@/components/dashboard/transactions/TransactionSection.vue"
import { useMoney } from "@/composables/useMoney"
import type { TransactionDetail } from "@/types"
import { breakdownLines } from "@/utils/transactionBreakdown"

const props = defineProps<{ transaction: TransactionDetail }>()

const format = useMoney()
const money = (amount: number) => format(amount, props.transaction.currency)

const lines = computed(() => breakdownLines(props.transaction.line_items))

const totals = computed(() => {
	const amounts = props.transaction.amounts
	const discountCode = amounts.coupon_code || amounts.access_code
	return [
		{ label: "Subtotal", value: money(amounts.net_amount), shown: true },
		{
			label: discountCode ? `Discount · ${discountCode}` : "Discount",
			value: `−${money(amounts.discount_amount)}`,
			shown: amounts.discount_amount > 0,
		},
		{
			label: `${amounts.tax_label || "Tax"} (${amounts.tax_percentage}%)`,
			value: money(amounts.tax_amount),
			shown: amounts.tax_amount > 0,
		},
	].filter((row) => row.shown)
})
</script>

<template>
	<TransactionSection title="Breakdown">
		<ul class="space-y-2 text-base">
			<li v-for="line in lines" :key="line.key" class="flex items-baseline gap-3">
				<span
					class="min-w-0 flex-1 truncate"
					:class="line.addOn ? 'text-ink-gray-6' : 'text-ink-gray-8'"
				>
					<span
						v-if="line.addOn"
						class="lucide-corner-down-right mr-1 inline-block size-3.5 align-[-2px] text-ink-gray-4"
						aria-hidden="true"
					/>
					{{ line.label }}
					<span class="text-sm tabular-nums text-ink-gray-5">
						{{ line.count }} × {{ money(line.unitPrice) }}
					</span>
				</span>
				<span class="shrink-0 tabular-nums text-ink-gray-8">{{
					money(line.count * line.unitPrice)
				}}</span>
			</li>
		</ul>

		<dl class="space-y-2 border-t border-outline-gray-2 pt-3 text-base">
			<div v-for="row in totals" :key="row.label" class="flex items-baseline justify-between gap-3">
				<dt class="text-ink-gray-5">{{ row.label }}</dt>
				<dd class="tabular-nums text-ink-gray-7">{{ row.value }}</dd>
			</div>
			<div class="flex items-baseline justify-between gap-3 border-t border-outline-gray-1 pt-2">
				<dt class="font-medium text-ink-gray-9">Total</dt>
				<dd class="font-medium tabular-nums text-ink-gray-9">
					{{ money(transaction.amounts.total_amount) }}
				</dd>
			</div>
			<template v-if="transaction.amounts.refunded_amount > 0">
				<div class="flex items-baseline justify-between gap-3">
					<dt class="text-ink-gray-5">Refunded</dt>
					<dd class="tabular-nums text-ink-red-4">
						−{{ money(transaction.amounts.refunded_amount) }}
					</dd>
				</div>
				<div class="flex items-baseline justify-between gap-3">
					<dt class="font-medium text-ink-gray-9">Net received</dt>
					<dd class="font-medium tabular-nums text-ink-gray-9">
						{{ money(transaction.amounts.net_received) }}
					</dd>
				</div>
			</template>
		</dl>
	</TransactionSection>
</template>
