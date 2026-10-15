<script setup lang="ts">
import { computed } from "vue"

import type { AvailableTicketType, BookingTicketCategory } from "@/types"
import { formatPriceOrFree } from "@/utils/currency"
import { groupTicketTypes } from "@/utils/ticketCategories"

// What each category holds, shown once an organizer describes a category.
const props = defineProps<{
	ticketTypes: AvailableTicketType[]
	categories: BookingTicketCategory[]
}>()

const groups = computed(() => groupTicketTypes(props.ticketTypes, props.categories))
const described = computed(() => props.categories.some((category) => category.description))
</script>

<template>
	<section
		v-if="described"
		class="mb-6 space-y-5 rounded-7 border border-outline-gray-3 bg-surface-base p-4 shadow-sm md:p-6"
	>
		<h4 class="text-lg-semibold text-ink-gray-9">{{ __("Tickets") }}</h4>
		<div v-for="group in groups" :key="group.category?.name ?? 'other'" class="space-y-2">
			<div>
				<h5 class="text-base font-semibold text-ink-gray-8">
					{{ group.category ? __(group.category.title) : __("Other tickets") }}
				</h5>
				<p v-if="group.category?.description" class="text-p-sm text-ink-gray-5">
					{{ group.category.description }}
				</p>
			</div>
			<ul class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
				<li
					v-for="ticketType in group.ticketTypes"
					:key="ticketType.name"
					class="flex items-center justify-between gap-3 px-3 py-2.5"
				>
					<span class="min-w-0 text-base text-ink-gray-9">{{ __(ticketType.title ?? "") }}</span>
					<span class="whitespace-nowrap text-base font-medium tabular-nums text-ink-gray-8">
						{{ formatPriceOrFree(ticketType.price, ticketType.currency) }}
					</span>
				</li>
			</ul>
		</div>
	</section>
</template>
