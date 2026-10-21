<script setup lang="ts">
import { type ButtonProps, ErrorMessage, Skeleton } from "frappe-ui"
import { computed } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import { ListFilters } from "@/components/common/filters"
import SectionHeader from "@/components/common/SectionHeader.vue"
import SponsorCard from "@/components/dashboard/sponsorships/SponsorCard.vue"
import { useListQuery } from "@/composables/useListQuery"
import { useEventSponsors } from "@/data/sponsorships"
import type { FrappeError, SponsorshipTierItem } from "@/types"

const props = defineProps<{
	event: string
	tiers: SponsorshipTierItem[]
	action?: (ButtonProps & { onClick: () => void }) | null
}>()
defineEmits<{ open: [sponsor: string] }>()

// Prefixed: the enquiries list on the same page owns the plain params.
const { search, order, conditions, isFiltered } = useListQuery("sponsor_")
const list = useEventSponsors(props.event, search, order, conditions)

defineExpose({ reload: list.reload })

// Highest-priced tier first, the order a sponsor wall reads in; the server's order holds within a tier.
const sponsors = computed(() => {
	const rank = new Map(props.tiers.map((tier) => [tier.name, tier.prices[0].price]))
	return (list.data?.sponsors ?? []).toSorted(
		(a, b) => (rank.get(b.tier ?? "") ?? 0) - (rank.get(a.tier ?? "") ?? 0),
	)
})

const errorMessage = computed(() => (list.error as FrappeError | null)?.message)
</script>

<template>
	<section class="space-y-3" aria-label="Sponsors">
		<SectionHeader title="Sponsors" :count="list.data?.total" :action="action" />

		<ListFilters
			v-if="list.data?.total || isFiltered"
			v-model="conditions"
			v-model:search="search"
			v-model:order="order"
			:fields="list.data?.filter_fields ?? []"
			search-placeholder="Search by company, email or website"
			disable-shortcut
		/>

		<p v-if="isFiltered" aria-live="polite" class="text-sm text-ink-gray-5">
			{{ sponsors.length }} of {{ list.data?.total ?? 0 }} sponsors
		</p>

		<div v-if="list.loading && !list.data" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
			<Skeleton v-for="card in 3" :key="card" class="h-40 w-full rounded-4" />
		</div>
		<ErrorMessage v-else-if="errorMessage" :message="errorMessage" />
		<div v-else-if="sponsors.length" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
			<SponsorCard
				v-for="sponsor in sponsors"
				:key="sponsor.name"
				:sponsor="sponsor"
				@open="$emit('open', sponsor.name)"
			/>
		</div>
		<EmptyState
			v-else-if="isFiltered"
			title="No matching sponsors"
			:description="
				search.trim()
					? `No sponsor matches “${search.trim()}”.`
					: 'No sponsor matches these filters.'
			"
			icon="lucide-filter-x"
		/>
		<EmptyState
			v-else
			title="No sponsors yet"
			description="Sponsors appear here once they pay or are confirmed by the team."
			icon="lucide-handshake"
		/>
	</section>
</template>
