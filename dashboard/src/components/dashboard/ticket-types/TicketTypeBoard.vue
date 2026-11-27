<script setup lang="ts">
import { useResizeObserver, useScroll } from "@vueuse/core"
import { Badge, Icon, Progress } from "frappe-ui"
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
// Uncategorized stays pinned on the left; columns scroll under it, so that edge never fades.
const pinned = computed(() => props.organizer.groups.value[0]?.category === null)
const edgeMask = computed(() => {
	const left = arrivedState.left || pinned.value ? "black" : "transparent"
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
			:class="[
				organizer.dropTarget.value === group.key
					? 'border-outline-gray-4 bg-surface-gray-2'
					: 'border-transparent bg-surface-gray-1 dark:bg-surface-base',
				{ 'sticky left-0 z-[1]': !group.category },
			]"
			v-on="canWrite ? organizer.drag.zone(group.key) : {}"
		>
			<header class="group flex min-h-7 items-center gap-1.5 pl-1">
				<Icon
					v-if="!group.category"
					icon="lucide-circle-dashed"
					class="size-4 shrink-0 text-ink-gray-5"
					aria-hidden="true"
				/>
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
					:first="!organizer.groups.value[index - 1]?.category"
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
					class="flex flex-col gap-2.5 rounded-4 border border-outline-gray-2 bg-surface-elevation-2 p-3 text-left transition-[border-color,opacity,transform] duration-150 ease-out enabled:active:scale-[0.98] [@media(hover:hover)]:enabled:hover:border-outline-gray-3 motion-reduce:transform-none"
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

			<button
				v-if="!group.ticketTypes.length && canWrite && !organizer.dragging.value"
				type="button"
				class="flex h-[4.5rem] items-center justify-center gap-1.5 rounded-4 border border-dashed border-outline-gray-3 text-sm text-ink-gray-6 transition-[border-color,color,transform] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] [@media(hover:hover)]:hover:border-outline-gray-4 [@media(hover:hover)]:hover:text-ink-gray-8 active:scale-[0.98] motion-reduce:transform-none"
				@click="$emit('add', group.key)"
			>
				<Icon icon="lucide-plus" class="size-4" aria-hidden="true" />
				Add ticket type
			</button>
			<p
				v-else-if="!group.ticketTypes.length"
				class="rounded-4 border border-dashed border-outline-gray-3 px-3 py-5 text-center text-sm text-ink-gray-5"
			>
				{{ organizer.dragging.value ? "Drop here to move" : "No ticket types yet" }}
			</p>
		</section>
	</div>
</template>
