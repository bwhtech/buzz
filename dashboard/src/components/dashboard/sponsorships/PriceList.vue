<script setup lang="ts">
import { FormControl, Tooltip } from "frappe-ui"
import { TooltipProvider } from "reka-ui"
import { computed } from "vue"

import PriceInput from "@/components/dashboard/sponsorships/PriceInput.vue"
import SortableList from "@/components/dashboard/sponsorships/SortableList.vue"
import { useEnabledCurrencies } from "@/data/currencies"
import type { TierPrice } from "@/types"

const prices = defineModel<TierPrice[]>({ required: true })
const props = defineProps<{
	disabled?: boolean
	lockedCurrencies?: string[]
	// Explains a locked row on hover, or on tap since the row takes focus.
	lockedMessage?: string
}>()

const isLocked = (row: TierPrice) => Boolean(props.lockedCurrencies?.includes(row.currency))

const enabledCurrencies = useEnabledCurrencies()

// A price keeps its currency even if the site later disables it.
const allCurrencies = computed(() => {
	const currencyNames = (enabledCurrencies.data ?? []).map((currency) => currency.name)
	const heldCurrencies = prices.value
		.map((row) => row.currency)
		.filter((name) => !currencyNames.includes(name))
	return [...heldCurrencies, ...currencyNames]
})

function currencyOptions(index: number) {
	const usedElsewhere = prices.value
		.filter((_, rowIndex) => rowIndex !== index)
		.map((row) => row.currency)
	return allCurrencies.value.filter((name) => !usedElsewhere.includes(name))
}

function currencyDetails(name: string) {
	return enabledCurrencies.data?.find((currency) => currency.name === name)
}

function createPrice(): TierPrice {
	const used = prices.value.map((row) => row.currency)
	return { currency: allCurrencies.value.find((name) => !used.includes(name)) ?? "", price: 0 }
}

function updatePrice(index: number, values: Partial<TierPrice>) {
	prices.value = prices.value.map((row, rowIndex) =>
		rowIndex === index ? { ...row, ...values } : row,
	)
}
</script>

<template>
	<!-- A click on a locked row keeps its tooltip open instead of dismissing it. -->
	<TooltipProvider :delay-duration="300" disable-closing-trigger>
		<SortableList
			v-model="prices"
			label="Prices"
			add-label="Add currency"
			item-name="price"
			:create-item="createPrice"
			:min-rows="1"
			:disabled="disabled"
			:is-locked="isLocked"
		>
			<template #row="{ item, index }">
				<Tooltip :disabled="!isLocked(item)">
					<template #content>
						<p class="max-w-64 text-p-xs">{{ lockedMessage }}</p>
					</template>
					<div
						class="grid min-w-0 flex-1 grid-cols-[2fr_1fr] gap-2 rounded-4 focus-visible:outline-none focus-visible:focus-ring"
						:tabindex="isLocked(item) ? 0 : undefined"
						:class="{ 'cursor-not-allowed [&_*]:!cursor-not-allowed': isLocked(item) }"
					>
						<PriceInput
							:model-value="item.price"
							aria-label="Price"
							:currency-symbol="currencyDetails(item.currency)?.symbol || item.currency"
							:number-format="currencyDetails(item.currency)?.number_format"
							:disabled="disabled || isLocked(item)"
							@update:model-value="updatePrice(index, { price: $event })"
						/>
						<FormControl
							:model-value="item.currency"
							type="select"
							aria-label="Currency"
							:options="currencyOptions(index)"
							:disabled="disabled || isLocked(item)"
							@update:model-value="updatePrice(index, { currency: $event })"
						/>
					</div>
				</Tooltip>
			</template>
		</SortableList>
	</TooltipProvider>
</template>
