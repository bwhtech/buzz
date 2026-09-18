<script setup lang="ts">
import { Badge } from "frappe-ui"
import { computed } from "vue"

import type { SponsorshipTierItem } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

const props = defineProps<{ tier: SponsorshipTierItem; canWrite?: boolean }>()
defineEmits<{ open: [] }>()

const price = computed(() => formatWholePriceOrFree(props.tier.price, props.tier.currency || "INR"))

const sponsors = computed(() => {
	const count = props.tier.sponsor_count
	if (!count) return "No sponsors"
	return `${count} sponsor${count === 1 ? "" : "s"}`
})
</script>

<template>
	<button
		type="button"
		class="flex w-full flex-col gap-2 rounded-4 border border-outline-gray-2 p-4 text-left transition-[background-color,transform] duration-150 ease-out enabled:hover:bg-surface-gray-1 enabled:active:scale-[0.98] focus-visible:focus-ring disabled:cursor-default motion-reduce:transform-none"
		:class="{ 'opacity-60': !tier.enabled }"
		:disabled="!canWrite"
		@click="$emit('open')"
	>
		<div class="flex items-center justify-between gap-2">
			<h3 class="min-w-0 truncate text-lg text-ink-gray-7">{{ tier.title }}</h3>
			<Badge v-if="!tier.enabled" theme="red" variant="subtle" label="Disabled" />
		</div>
		<p class="truncate text-6xl font-semibold text-ink-gray-9">{{ price }}</p>
		<span class="mt-3 text-base text-ink-gray-5">{{ sponsors }}</span>
	</button>
</template>
