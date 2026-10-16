<template>
	<div class="flex flex-col text-p-sm">
		<p v-if="!lines.length" class="px-4 pb-4 text-ink-gray-5">
			{{ __("No tickets selected yet") }}
		</p>
		<ul v-else class="flex flex-col gap-2.5 px-4 pb-3.5">
			<li v-for="line in lines" :key="line.key" class="flex justify-between gap-3">
				<div class="flex min-w-0 flex-col">
					<span class="text-ink-gray-8">{{ __(line.title) }}</span>
					<span class="text-xs text-ink-gray-5">× {{ line.count }}</span>
				</div>
				<span class="tabular-nums text-ink-gray-8">
					{{ formatWholePriceOrFree(line.amount, currency) }}
				</span>
			</li>
		</ul>
		<div v-if="$slots.coupon" class="border-t border-outline-gray-2 px-4 py-3">
			<slot name="coupon" />
		</div>
		<dl class="flex flex-col gap-1.5 border-t border-outline-gray-2 px-4 py-3 tabular-nums">
			<template v-if="totals.subtotal > 0">
				<!-- An inclusive price with no discount makes the subtotal the total. -->
				<div
					v-if="!taxInclusive || totals.discount > 0"
					class="flex justify-between text-ink-gray-6"
				>
					<dt>{{ __("Subtotal") }}</dt>
					<dd>{{ format(totals.subtotal) }}</dd>
				</div>
				<div v-if="totals.discount > 0" class="flex justify-between text-ink-green-7">
					<dt>{{ discountLabel }}</dt>
					<dd>− {{ format(totals.discount) }}</dd>
				</div>
				<div v-if="totals.tax > 0 && !taxInclusive" class="flex justify-between text-ink-gray-6">
					<dt>{{ taxLine }}</dt>
					<dd>{{ format(totals.tax) }}</dd>
				</div>
			</template>
			<div class="flex items-baseline justify-between pt-1.5 text-lg font-semibold text-ink-gray-9">
				<dt>{{ __("Total") }}</dt>
				<dd class="flex items-baseline gap-1.5">
					<span v-if="totals.discount > 0" class="text-xs font-normal text-ink-gray-5 line-through">
						{{ format(totals.before) }}
					</span>
					{{ formatWholePriceOrFree(totals.total, currency) }}
				</dd>
			</div>
			<p v-if="totals.tax > 0 && taxInclusive" class="text-right text-xs text-ink-gray-5">
				{{ __("Inclusive of {0} {1}", [format(totals.tax), taxLine]) }}
			</p>
		</dl>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue"

import { formatWholePriceOrFree } from "@/utils/currency"

export interface SummaryLineItem {
	key: string
	title: string
	count: number
	amount: number
}

export interface OrderTotals {
	subtotal: number
	discount: number
	tax: number
	total: number
	before: number
}

const props = defineProps<{
	lines: SummaryLineItem[]
	totals: OrderTotals
	currency: string
	taxLabel: string
	taxPercentage: number
	taxInclusive: boolean
	discountLabel: string
}>()

const format = (amount: number) => formatWholePriceOrFree(amount, props.currency)
const taxLine = computed(() => `${__(props.taxLabel)} (${props.taxPercentage}%)`)
</script>
