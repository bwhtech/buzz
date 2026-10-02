<script setup lang="ts">
import { Badge, Icon, Progress } from "frappe-ui"

import type { TierPrice } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

// A tier or ticket type in a list: name, prices, and how much of it is taken.
defineProps<{
	title: string
	subtitle: string
	prices: TierPrice[]
	usageLabel: string
	// Shown as a bar only when the item has a cap.
	usagePercent?: number | null
	badge?: { label: string; theme: "red" | "amber" | "gray" } | null
	muted?: boolean
	disabled?: boolean
}>()

const formatPrice = (row: TierPrice) => formatWholePriceOrFree(row.price, row.currency)
</script>

<template>
	<button
		type="button"
		class="grid w-full grid-cols-1 items-center gap-3 rounded-4 border border-outline-gray-2 p-3 text-left transition-[background-color,transform] duration-150 ease-out [@media(hover:hover)]:enabled:hover:bg-surface-gray-1 enabled:active:scale-[0.99] focus-visible:outline-none focus-visible:focus-ring disabled:cursor-default motion-reduce:transform-none sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1.4fr)_minmax(0,1fr)_1rem]"
		:class="{ 'opacity-60': muted }"
		:disabled="disabled"
	>
		<span class="min-w-0 space-y-1">
			<span class="flex items-center gap-2">
				<span class="truncate text-base font-medium text-ink-gray-9">{{ title }}</span>
				<Badge v-if="badge" :theme="badge.theme" variant="subtle" :label="badge.label" />
			</span>
			<span class="block text-sm text-ink-gray-5">{{ subtitle }}</span>
		</span>

		<span class="min-w-0 space-y-1">
			<span class="block truncate text-base font-semibold tabular-nums text-ink-gray-9">
				{{ prices[0] && formatPrice(prices[0]) }}
			</span>
			<span v-if="prices.length > 1" class="block truncate text-sm tabular-nums text-ink-gray-5">
				{{ prices.slice(1).map(formatPrice).join(" · ") }}
			</span>
		</span>

		<span class="min-w-0 space-y-1.5">
			<span class="block text-sm tabular-nums text-ink-gray-6">{{ usageLabel }}</span>
			<!-- The label above already reads the same count out. -->
			<Progress
				v-if="usagePercent != null"
				aria-hidden="true"
				size="sm"
				:value="Math.min(usagePercent, 100)"
			/>
		</span>

		<Icon
			v-if="!disabled"
			name="lucide-chevron-right"
			class="hidden size-4 text-ink-gray-4 sm:block"
		/>
	</button>
</template>
