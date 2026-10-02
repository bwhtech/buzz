<script setup lang="ts">
import { Badge, Icon, Progress } from "frappe-ui"

import type { SponsorshipTierItem, TierPrice } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

defineProps<{ tiers: SponsorshipTierItem[]; canWrite?: boolean }>()
defineEmits<{ open: [name: string] }>()

const isFull = (tier: SponsorshipTierItem) => tier.slots > 0 && tier.sponsor_count >= tier.slots

const formatPrice = (row: TierPrice) => formatWholePriceOrFree(row.price, row.currency)

// A tier without a slot count takes any number of sponsors.
function slotsLabel(tier: SponsorshipTierItem) {
	if (!tier.slots) return `Unlimited · ${tier.sponsor_count} taken`
	return `${tier.sponsor_count} of ${tier.slots} taken`
}

function perkCount(tier: SponsorshipTierItem) {
	const count = (tier.perks ?? "").split("\n").filter((perk) => perk.trim()).length
	return `${count} perk${count === 1 ? "" : "s"}`
}
</script>

<template>
	<ul class="space-y-2">
		<li v-for="tier in tiers" :key="tier.name">
			<button
				type="button"
				class="grid w-full grid-cols-1 items-center gap-3 rounded-4 border border-outline-gray-2 p-3 text-left transition-[background-color,transform] duration-150 ease-out [@media(hover:hover)]:enabled:hover:bg-surface-gray-1 enabled:active:scale-[0.99] focus-visible:outline-none focus-visible:focus-ring disabled:cursor-default motion-reduce:transform-none sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1.4fr)_minmax(0,1fr)_1rem]"
				:class="{ 'opacity-60': !tier.enabled }"
				:disabled="!canWrite"
				@click="$emit('open', tier.name)"
			>
				<span class="min-w-0 space-y-1">
					<span class="flex items-center gap-2">
						<span class="truncate text-base font-medium text-ink-gray-9">{{ tier.title }}</span>
						<Badge v-if="!tier.enabled" theme="red" variant="subtle" label="Disabled" />
						<Badge v-else-if="isFull(tier)" theme="amber" variant="subtle" label="Full" />
					</span>
					<span class="block text-sm text-ink-gray-5">{{ perkCount(tier) }}</span>
				</span>

				<span class="min-w-0 space-y-1">
					<span class="block truncate text-base font-semibold tabular-nums text-ink-gray-9">
						{{ formatPrice(tier.prices[0]) }}
					</span>
					<span
						v-if="tier.prices.length > 1"
						class="block truncate text-sm tabular-nums text-ink-gray-5"
					>
						{{ tier.prices.slice(1).map(formatPrice).join(" · ") }}
					</span>
				</span>

				<span class="min-w-0 space-y-1.5">
					<span class="block text-sm tabular-nums text-ink-gray-6">{{ slotsLabel(tier) }}</span>
					<!-- The label above already reads the same count out. -->
					<Progress
						v-if="tier.slots"
						aria-hidden="true"
						size="sm"
						:value="Math.min((tier.sponsor_count / tier.slots) * 100, 100)"
					/>
				</span>

				<Icon
					v-if="canWrite"
					name="lucide-chevron-right"
					class="hidden size-4 text-ink-gray-4 sm:block"
				/>
			</button>
		</li>
	</ul>
</template>
