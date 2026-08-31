<script setup lang="ts">
import type { TicketAddOnDetail } from "@/types"
import { formatCurrency } from "@/utils/currency"

defineProps<{ addOns: TicketAddOnDetail[] }>()

const price = (amount: number | null, currency: string | null) =>
	amount ? formatCurrency(amount, currency || undefined) : "Included"
</script>

<template>
	<div v-if="addOns.length" class="flex flex-col gap-2 px-4 pb-4">
		<h3 class="text-p-xs uppercase tracking-wide text-ink-gray-5">Add-ons</h3>
		<ul class="flex flex-col divide-y divide-outline-gray-1 border-t border-outline-gray-1">
			<li v-for="addOn in addOns" :key="addOn.id" class="flex items-baseline gap-4 py-2">
				<div class="min-w-0 flex-1">
					<p class="truncate text-p-base text-ink-gray-8">{{ addOn.title }}</p>
					<!-- Only a selectable add-on carries a chosen value worth stating. -->
					<p v-if="addOn.value" class="truncate text-p-sm text-ink-gray-5">{{ addOn.value }}</p>
				</div>
				<span class="shrink-0 font-mono text-p-base tabular-nums text-ink-gray-7">
					{{ price(addOn.price, addOn.currency) }}
				</span>
			</li>
		</ul>
	</div>
</template>
