<script setup lang="ts">
import PricedItemRow from "@/components/common/PricedItemRow.vue"
import type { SponsorshipTierItem } from "@/types"

defineProps<{ tiers: SponsorshipTierItem[]; canWrite?: boolean }>()
defineEmits<{ open: [name: string] }>()

const isFull = (tier: SponsorshipTierItem) => tier.slots > 0 && tier.sponsor_count >= tier.slots

function badge(tier: SponsorshipTierItem) {
	if (!tier.enabled) return { label: "Disabled", theme: "red" as const }
	return isFull(tier) ? { label: "Full", theme: "amber" as const } : null
}

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
			<PricedItemRow
				:title="tier.title"
				:subtitle="perkCount(tier)"
				:prices="tier.prices"
				:usage-label="slotsLabel(tier)"
				:usage-percent="tier.slots ? (tier.sponsor_count / tier.slots) * 100 : null"
				:badge="badge(tier)"
				:muted="!tier.enabled"
				:disabled="!canWrite"
				@click="$emit('open', tier.name)"
			/>
		</li>
	</ul>
</template>
