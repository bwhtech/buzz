<template>
	<div class="flex flex-col gap-7">
		<section
			v-for="group in groups"
			:key="group.category?.name ?? 'other'"
			class="flex flex-col gap-2.5"
		>
			<div
				v-if="groups.length > 1 || group.category"
				class="flex flex-col gap-0.5 md:flex-row md:items-baseline md:justify-between md:gap-3"
			>
				<h2 class="text-lg font-semibold text-ink-gray-9">
					{{ group.category ? __(group.category.title) : __("Other tickets") }}
				</h2>
				<p v-if="group.category?.description" class="text-p-sm text-ink-gray-5">
					{{ group.category.description }}
				</p>
			</div>
			<ul
				class="flex flex-col divide-y divide-outline-gray-2 overflow-hidden rounded-[14px] border border-outline-gray-2 md:rounded-7"
			>
				<li
					v-for="ticketType in group.ticketTypes"
					:key="ticketType.name"
					class="flex flex-col gap-3 bg-surface-base p-3.5 md:flex-row md:items-center md:gap-4 md:px-4"
					:class="{ 'opacity-60': ticketType.price_note }"
				>
					<div class="flex min-w-0 flex-1 flex-col gap-1">
						<span class="text-base font-semibold text-ink-gray-9 text-pretty">
							{{ __(ticketType.title ?? "") }}
						</span>
						<span v-if="ticketType.description" class="text-p-sm text-ink-gray-5 text-pretty">
							{{ __(ticketType.description) }}
						</span>
					</div>
					<div class="flex items-center justify-between gap-4 md:justify-end">
						<span class="text-lg font-semibold tabular-nums text-ink-gray-9 md:text-base">
							{{ formatWholePriceOrFree(ticketType.price, ticketType.currency) }}
						</span>
						<div class="flex min-w-[104px] justify-end">
							<span
								v-if="ticketType.price_note"
								class="whitespace-nowrap text-p-sm text-ink-gray-5"
							>
								{{ __("Not sold in {0}", [currency]) }}
							</span>
							<QuantityStepper
								v-else
								:quantity="quantities[String(ticketType.name)] ?? 0"
								:label="ticketType.title ?? ''"
								:size="stepperSize"
								@change="emit('change', ticketType, $event)"
							/>
						</div>
					</div>
				</li>
			</ul>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue"

import type { AvailableTicketType, BookingTicketCategory } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"
import { groupTicketTypes } from "@/utils/ticketCategories"

import QuantityStepper from "./QuantityStepper.vue"

const props = defineProps<{
	ticketTypes: AvailableTicketType[]
	categories: BookingTicketCategory[]
	quantities: Record<string, number>
	currency: string
	stepperSize?: "sm" | "lg"
}>()
const emit = defineEmits<{ change: [ticketType: AvailableTicketType, delta: number] }>()

const groups = computed(() => groupTicketTypes(props.ticketTypes, props.categories))
</script>
