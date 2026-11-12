<script setup lang="ts">
import { computed } from "vue"

import TransactionSection from "@/components/dashboard/transactions/TransactionSection.vue"
import { useMoney } from "@/composables/useMoney"
import type { TransactionDetail } from "@/types"

const props = defineProps<{ transaction: TransactionDetail }>()

const format = useMoney()
const money = (amount: number) => format(amount, props.transaction.currency)

const totals = computed(() => {
	const amounts = props.transaction.amounts
	const discountCode = amounts.coupon_code || amounts.access_code
	const taxLabel = `${amounts.tax_label || "Tax"} (${amounts.tax_percentage}%)`
	return [
		{ label: "Subtotal", value: money(amounts.net_amount), shown: true },
		{
			label: discountCode ? `Discount · ${discountCode}` : "Discount",
			value: `−${money(amounts.discount_amount)}`,
			shown: amounts.discount_amount > 0,
		},
		{ label: taxLabel, value: money(amounts.tax_amount), shown: amounts.tax_amount > 0 },
		{ label: "Total", value: money(amounts.total_amount), shown: true, strong: true },
		{
			label: "Refunded",
			value: `−${money(amounts.refunded_amount)}`,
			shown: amounts.refunded_amount > 0,
		},
		{
			label: "Net received",
			value: money(amounts.net_received),
			shown: amounts.refunded_amount > 0,
			strong: true,
		},
	].filter((row) => row.shown)
})
</script>

<template>
	<TransactionSection title="Amounts">
		<ul class="divide-y divide-outline-gray-1 text-base">
			<li
				v-for="(item, index) in transaction.line_items"
				:key="index"
				class="flex items-baseline gap-3 py-2"
			>
				<span class="min-w-0 flex-1">
					<span class="block truncate text-ink-gray-8">
						{{ item.ticket_type || "Ticket" }} · {{ item.attendee_name || item.attendee_email }}
					</span>
					<span v-if="item.add_ons.length" class="block truncate text-sm text-ink-gray-5">
						{{ item.add_ons.join(", ") }} · {{ money(item.add_on_total) }}
					</span>
				</span>
				<span class="shrink-0 tabular-nums text-ink-gray-8">{{ money(item.amount) }}</span>
			</li>
		</ul>

		<dl class="space-y-2 border-t border-outline-gray-2 pt-3 text-base">
			<div v-for="row in totals" :key="row.label" class="flex items-baseline justify-between gap-3">
				<dt :class="row.strong ? 'font-medium text-ink-gray-9' : 'text-ink-gray-5'">
					{{ row.label }}
				</dt>
				<dd
					class="tabular-nums"
					:class="row.strong ? 'font-medium text-ink-gray-9' : 'text-ink-gray-7'"
				>
					{{ row.value }}
				</dd>
			</div>
		</dl>
	</TransactionSection>
</template>
