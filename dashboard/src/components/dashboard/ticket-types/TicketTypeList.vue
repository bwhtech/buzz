<script setup lang="ts">
import { dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import PricedItemRow from "@/components/common/PricedItemRow.vue"
import type { TicketCategoryItem, TicketTypeItem } from "@/types"

type TicketGroup = {
	category: TicketCategoryItem | null
	title: string
	ticketTypes: TicketTypeItem[]
}

const props = defineProps<{
	ticketTypes: TicketTypeItem[]
	categories: TicketCategoryItem[]
	canWrite?: boolean
}>()
defineEmits<{ open: [name: string]; editCategory: [category: TicketCategoryItem] }>()

// Categories arrive in display order. Without any, the list stays flat under one untitled group.
const groups = computed<TicketGroup[]>(() => {
	const inCategory = (name: string | null) =>
		props.ticketTypes.filter((ticketType) => (ticketType.category || null) === name)
	const categorized = props.categories.map((category) => ({
		category,
		title: category.title,
		ticketTypes: inCategory(category.name),
	}))
	const uncategorized = inCategory(null)
	if (!categorized.length) return [{ category: null, title: "", ticketTypes: uncategorized }]
	if (!uncategorized.length) return categorized
	return [...categorized, { category: null, title: "Uncategorized", ticketTypes: uncategorized }]
})

const isSoldOut = (ticketType: TicketTypeItem) =>
	ticketType.max_tickets_available > 0 &&
	ticketType.tickets_sold >= ticketType.max_tickets_available

function badge(ticketType: TicketTypeItem) {
	if (!ticketType.is_published) return { label: "Disabled", theme: "red" as const }
	return isSoldOut(ticketType) ? { label: "Sold out", theme: "amber" as const } : null
}

function salesLabel(ticketType: TicketTypeItem) {
	if (!ticketType.auto_unpublish_after) return "No end date"
	return `Sales end ${dayjsLocal(ticketType.auto_unpublish_after).format("D MMM YYYY")}`
}

// A ticket type without a seat count sells any number of tickets.
function seatsLabel(ticketType: TicketTypeItem) {
	const seats = ticketType.max_tickets_available
	if (!seats) return `Unlimited · ${ticketType.tickets_sold} sold`
	return `${ticketType.tickets_sold} of ${seats} sold`
}
</script>

<template>
	<div class="space-y-6">
		<section
			v-for="group in groups"
			:key="group.category?.name ?? 'uncategorized'"
			class="space-y-2"
		>
			<button
				v-if="group.category"
				type="button"
				class="block w-full rounded-4 px-3 py-1 text-left enabled:hover:bg-surface-gray-1"
				:disabled="!canWrite"
				@click="$emit('editCategory', group.category)"
			>
				<h3 class="text-base font-medium text-ink-gray-8">{{ group.title }}</h3>
				<p v-if="group.category.description" class="text-p-sm text-ink-gray-5">
					{{ group.category.description }}
				</p>
			</button>
			<h3 v-else-if="group.title" class="px-3 text-base font-medium text-ink-gray-8">
				{{ group.title }}
			</h3>
			<p v-if="!group.ticketTypes.length" class="px-3 text-sm text-ink-gray-5">
				No ticket types in this category yet.
			</p>
			<ul class="space-y-2">
				<li v-for="ticketType in group.ticketTypes" :key="ticketType.name">
					<PricedItemRow
						:title="ticketType.title"
						:subtitle="salesLabel(ticketType)"
						:prices="ticketType.prices"
						:usage-label="seatsLabel(ticketType)"
						:usage-percent="
							ticketType.max_tickets_available
								? (ticketType.tickets_sold / ticketType.max_tickets_available) * 100
								: null
						"
						:badge="badge(ticketType)"
						:muted="!ticketType.is_published"
						:disabled="!canWrite"
						@click="$emit('open', ticketType.name)"
					/>
				</li>
			</ul>
		</section>
	</div>
</template>
