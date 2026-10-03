<script setup lang="ts">
import { NumberCard } from "frappe-ui/charts"
import { computed } from "vue"

import type { CurrencyRevenue } from "@/types"
import { formatCurrency, getCurrencySymbol } from "@/utils/currency"

const props = defineProps<{ revenue: CurrencyRevenue[] }>()

const money = (amount: number, currency: string) =>
	formatCurrency(amount, currency, "en-US", { maximumFractionDigits: 0 })

const net = (row: CurrencyRevenue) => row.collected - row.refunded

// Currencies are never summed: the one with the most bookings is the reading, the rest
// ride in its caption.
const sorted = computed(() => props.revenue.toSorted((a, b) => b.bookings - a.bookings))
const main = computed(() => sorted.value[0])

const revenueCaption = computed(() => {
	const others = sorted.value.slice(1).map((row) => `+ ${money(net(row), row.currency)}`)
	const refunded = main.value.refunded
		? [`${money(main.value.refunded, main.value.currency)} refunded`]
		: []
	return [...others, ...refunded].join(" · ")
})

const symbol = computed(() => getCurrencySymbol(main.value.currency))

// An average, so 1.7 is real; a whole one drops the ".0".
const ticketsPerBooking = computed(() => {
	const average = Number((main.value.tickets / main.value.bookings).toFixed(1))
	return `${average} ${average === 1 ? "ticket" : "tickets"} per booking`
})
</script>

<template>
	<div class="grid gap-4 sm:grid-cols-2">
		<NumberCard
			title="Revenue"
			:value="net(main)"
			:prefix="symbol"
			:precision="0"
			:delta-caption="revenueCaption"
		/>
		<NumberCard
			title="Average order"
			:value="main.collected / main.bookings"
			:prefix="symbol"
			:precision="0"
			:delta-caption="ticketsPerBooking"
		/>
	</div>
</template>
