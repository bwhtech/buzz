<script setup lang="ts">
import { Badge, Progress } from "frappe-ui"

import type { TicketTypeOrganizer } from "@/composables/useTicketTypeOrganizer"
import type { TicketCategoryItem } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"
import { salesLabel, seatsLabel, soldPercent, ticketTypeBadge } from "@/utils/ticketTypeLabels"

import TicketCategoryActions from "./TicketCategoryActions.vue"

defineProps<{ organizer: TicketTypeOrganizer; canWrite?: boolean }>()
defineEmits<{
	open: [name: string]
	add: [category: string]
	editCategory: [category: TicketCategoryItem]
}>()
</script>

<template>
	<div class="-mx-1 flex items-start gap-2.5 overflow-x-auto px-1 pb-2">
		<section
			v-for="(group, index) in organizer.groups.value"
			:key="group.key"
			class="flex w-64 shrink-0 flex-col gap-1.5 rounded-xl p-1.5 outline-dashed outline-[1.5px] -outline-offset-[1.5px] transition-colors duration-150 ease-out"
			:class="
				organizer.dropTarget.value === group.key
					? 'bg-surface-gray-2 outline-outline-gray-4'
					: 'bg-surface-gray-1 outline-transparent'
			"
			v-on="canWrite ? organizer.drag.zone(group.key) : {}"
		>
			<header class="group flex min-h-7 items-center gap-1.5 pl-1.5">
				<h3
					class="truncate text-sm font-semibold"
					:class="group.category ? 'text-ink-gray-9' : 'text-ink-gray-6'"
				>
					{{ group.title }}
				</h3>
				<span class="flex-1 text-sm tabular-nums text-ink-gray-5">{{
					group.ticketTypes.length
				}}</span>
				<TicketCategoryActions
					v-if="canWrite"
					:category="group.category"
					:first="index === 0"
					:last="!organizer.groups.value[index + 1]?.category"
					horizontal
					@move="organizer.shift(group.category!, $event)"
					@edit="$emit('editCategory', group.category!)"
					@remove="organizer.remove(group.category!)"
					@add="$emit('add', group.key)"
				/>
			</header>

			<button
				v-for="ticketType in group.ticketTypes"
				:key="ticketType.name"
				type="button"
				class="flex flex-col gap-2.5 rounded-4 border border-outline-gray-2 bg-surface-base p-3 text-left transition-[box-shadow,opacity,transform] duration-150 ease-out focus-visible:outline-none focus-visible:focus-ring enabled:active:scale-[0.98] [@media(hover:hover)]:enabled:hover:shadow-sm motion-reduce:transform-none"
				:class="{
					'opacity-40': organizer.dragging.value === ticketType.name,
					'opacity-60': !ticketType.is_published,
				}"
				:disabled="!canWrite"
				:draggable="canWrite"
				v-on="canWrite ? organizer.drag.handle(ticketType) : {}"
				@click="$emit('open', ticketType.name)"
			>
				<span class="flex items-start justify-between gap-2">
					<span class="min-w-0 space-y-0.5">
						<span class="block text-sm font-medium text-ink-gray-9">{{ ticketType.title }}</span>
						<span class="block text-xs text-ink-gray-5">{{ salesLabel(ticketType) }}</span>
					</span>
					<span class="whitespace-nowrap text-sm font-semibold tabular-nums text-ink-gray-8">
						{{
							ticketType.prices[0] &&
							formatWholePriceOrFree(ticketType.prices[0].price, ticketType.prices[0].currency)
						}}
					</span>
				</span>
				<Progress
					v-if="soldPercent(ticketType) != null"
					aria-hidden="true"
					size="sm"
					:value="Math.min(soldPercent(ticketType)!, 100)"
				/>
				<span class="flex items-center justify-between gap-2">
					<span class="text-xs tabular-nums text-ink-gray-6">{{ seatsLabel(ticketType) }}</span>
					<Badge
						v-if="ticketTypeBadge(ticketType)"
						variant="subtle"
						:theme="ticketTypeBadge(ticketType)!.theme"
						:label="ticketTypeBadge(ticketType)!.label"
					/>
				</span>
			</button>

			<p
				v-if="!group.ticketTypes.length"
				class="rounded-4 border border-dashed border-outline-gray-3 px-3 py-5 text-center text-sm text-ink-gray-5"
			>
				{{ organizer.dragging.value ? "Drop here to move" : "No ticket types yet" }}
			</p>
		</section>
	</div>
</template>
