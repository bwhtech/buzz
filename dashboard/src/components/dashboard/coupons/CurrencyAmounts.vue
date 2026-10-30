<script setup lang="ts">
import PriceInput from "@/components/dashboard/sponsorships/PriceInput.vue"
import { useEnabledCurrencies } from "@/data/currencies"
import type { TierPrice } from "@/types"
import { getCurrencySymbol } from "@/utils/currency"

// One amount per currency the coupon's ticket types sell in; rows for other currencies are kept
// out of view and dropped on save.
const amounts = defineModel<TierPrice[]>({ required: true })
defineProps<{ label: string; currencies: string[]; disabled?: boolean }>()

const enabledCurrencies = useEnabledCurrencies()
const details = (currency: string) => enabledCurrencies.data?.find((row) => row.name === currency)

function amountIn(currency: string) {
	return amounts.value.find((row) => row.currency === currency)?.price ?? 0
}

function setAmount(currency: string, price: number) {
	const others = amounts.value.filter((row) => row.currency !== currency)
	amounts.value = [...others, { currency, price }]
}
</script>

<template>
	<div class="space-y-1.5">
		<p class="text-xs text-ink-gray-5">{{ label }}</p>
		<div
			v-for="currency in currencies"
			:key="currency"
			class="grid grid-cols-[minmax(0,1fr)_4rem] items-center gap-2"
		>
			<PriceInput
				:model-value="amountIn(currency)"
				:currency-symbol="details(currency)?.symbol || getCurrencySymbol(currency)"
				:number-format="details(currency)?.number_format"
				:aria-label="`${label} in ${currency}`"
				:disabled="disabled"
				@update:model-value="setAmount(currency, $event)"
			/>
			<span class="text-sm text-ink-gray-5">{{ currency }}</span>
		</div>
	</div>
</template>
