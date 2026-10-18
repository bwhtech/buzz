<script setup lang="ts">
import { useResizeObserver, useScroll } from "@vueuse/core"
import { Badge, Progress } from "frappe-ui"
import { computed, useTemplateRef, watchPostEffect } from "vue"

import type { TicketTypeOrganizer } from "@/composables/useTicketTypeOrganizer"
import type { TicketCategoryItem } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"
import { salesLabel, seatsLabel, soldPercent, ticketTypeBadge } from "@/utils/ticketTypeLabels"

import TicketCategoryActions from "./TicketCategoryActions.vue"

const props = defineProps<{ organizer: TicketTypeOrganizer; canWrite?: boolean }>()
defineEmits<{
	open: [name: string]
	add: [category: string]
	editCategory: [category: TicketCategoryItem]
}>()

// Fades whichever edge has more columns past it, so a cut-off column reads as scrollable.
const board = useTemplateRef<HTMLElement>("board")
const { arrivedState, measure } = useScroll(board)
// useScroll measures only on scroll; columns and the page width change without one.
useResizeObserver(board, measure)
watchPostEffect(() => props.organizer.groups.value.length && measure())
const edgeMask = computed(() => {
	const left = arrivedState.left ? "black" : "transparent"
	const right = arrivedState.right ? "black" : "transparent"
	return `linear-gradient(to right, ${left}, black 2rem, black calc(100% - 2rem), ${right})`
})
</script>

<template>
	<div
		ref="board"
		class="-mx-1 flex items-start gap-3 overflow-x-auto px-1 pb-2"
		:style="{ maskImage: edgeMask }"
	>
		<section
			v-for="(group, index) in organizer.groups.value"
			:key="group.key"
			class="flex w-64 shrink-0 flex-col gap-2 rounded-7 border border-dashed p-2 transition-colors duration-150 ease-out"
			:class="
				organizer.dropTarget.value === group.key
					? 'border-outline-gray-4 bg-surface-gray-2'
					: 'border-transparent bg-surface-gray-1 dark:bg-surface-base'
			"
			v-on="canWrite ? organizer.drag.zone(group.key) : {}"
		>
			<header class="group flex min-h-7 items-center gap-1.5 pl-1">
				<h3
					class="truncate text-sm font-semibold"
					:title="group.title"
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
					menu
					@move="organizer.shift(group.category!, $event)"
					@edit="$emit('editCategory', group.category!)"
					@remove="organizer.remove(group.category!)"
					@add="$emit('add', group.key)"
				/>
			</header>

			<TransitionGroup
				enter-active-class="transition duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
				enter-from-class="-translate-y-1 opacity-0"
			>
				<button
					v-for="ticketType in group.ticketTypes"
					:key="ticketType.name"
					type="button"
					class="flex flex-col gap-2.5 rounded-4 border border-outline-gray-2 bg-surface-elevation-2 p-3 text-left transition-[box-shadow,opacity,transform] duration-150 ease-out focus-visible:outline-none focus-visible:focus-ring enabled:active:scale-[0.98] [@media(hover:hover)]:enabled:hover:shadow-sm motion-reduce:transform-none"
					:class="
						organizer.dragging.value === ticketType.name
							? 'opacity-40'
							: { 'opacity-60': !ticketType.is_published }
					"
					:disabled="!canWrite"
					:draggable="canWrite"
					v-on="canWrite ? organizer.drag.handle(ticketType) : {}"
					@click="$emit('open', ticketType.name)"
				>
					<span class="space-y-0.5">
						<span
							class="line-clamp-3 text-sm font-medium text-ink-gray-9 [overflow-wrap:anywhere]"
							:title="ticketType.title"
							>{{ ticketType.title }}</span
						>
						<span class="block text-xs text-ink-gray-5">{{ salesLabel(ticketType) }}</span>
					</span>
					<span class="text-sm font-semibold tabular-nums text-ink-gray-8">
						{{
							ticketType.prices[0] &&
							formatWholePriceOrFree(ticketType.prices[0].price, ticketType.prices[0].currency)
						}}
						<span v-if="ticketType.prices.length > 1" class="text-xs font-normal text-ink-gray-5">
							+{{ ticketType.prices.length - 1 }}
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
							v-bind="ticketTypeBadge(ticketType)!"
						/>
					</span>
				</button>
			</TransitionGroup>

			<p
				v-if="!group.ticketTypes.length"
				class="rounded-4 border border-dashed border-outline-gray-3 px-3 py-5 text-center text-sm text-ink-gray-5"
			>
				{{ organizer.dragging.value ? "Drop here to move" : "No ticket types yet" }}
			</p>
		</section>
	</div>
</template>
