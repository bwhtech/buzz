<script setup lang="ts">
import { Badge, Icon } from "frappe-ui"
import { reactive } from "vue"

import type { TicketTypeOrganizer } from "@/composables/useTicketTypeOrganizer"
import type { TicketCategoryItem } from "@/types"

import TicketCategoryActions from "./TicketCategoryActions.vue"
import TicketTypeRow from "./TicketTypeRow.vue"

defineProps<{ organizer: TicketTypeOrganizer; canWrite?: boolean }>()
defineEmits<{
	open: [name: string]
	add: [category: string]
	editCategory: [category: TicketCategoryItem]
}>()

const collapsed = reactive(new Set<string>())
const toggle = (key: string) => (collapsed.has(key) ? collapsed.delete(key) : collapsed.add(key))
</script>

<template>
	<div class="space-y-5">
		<section
			v-for="(group, index) in organizer.groups.value"
			:key="group.key"
			class="-m-1 space-y-1.5 rounded-6 border border-dashed p-1 transition-colors duration-150 ease-out"
			:class="
				organizer.dropTarget.value === group.key
					? 'border-outline-gray-4 bg-surface-gray-1'
					: 'border-transparent'
			"
			v-on="canWrite ? organizer.drag.zone(group.key) : {}"
		>
			<header class="group flex min-h-8 items-center gap-1.5 pl-1">
				<div class="min-w-0 flex-1">
					<h3>
						<button
							type="button"
							class="flex max-w-full items-center gap-1.5 rounded-3 py-0.5 text-left"
							:aria-expanded="!collapsed.has(group.key)"
							@click="toggle(group.key)"
						>
							<Icon
								icon="lucide-chevron-down"
								class="size-4 shrink-0 text-ink-gray-5 transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
								:class="{ '-rotate-90': collapsed.has(group.key) }"
								aria-hidden="true"
							/>
							<Icon
								v-if="!group.category"
								icon="lucide-circle-dashed"
								class="size-4 shrink-0 text-ink-gray-5"
								aria-hidden="true"
							/>
							<span
								class="min-w-0 text-base font-semibold [overflow-wrap:anywhere]"
								:class="group.category ? 'text-ink-gray-9' : 'text-ink-gray-6'"
							>
								{{ group.title }}
							</span>
							<Badge
								theme="gray"
								variant="subtle"
								class="tabular-nums"
								:label="String(group.ticketTypes.length)"
							/>
						</button>
					</h3>
					<p
						v-if="group.category?.description"
						class="truncate pl-[22px] text-sm text-ink-gray-5"
						:title="group.category.description"
					>
						{{ group.category.description }}
					</p>
				</div>
				<TicketCategoryActions
					v-if="canWrite"
					:category="group.category"
					:first="!organizer.groups.value[index - 1]?.category"
					:last="!organizer.groups.value[index + 1]?.category"
					@move="organizer.shift(group.category!, $event)"
					@edit="$emit('editCategory', group.category!)"
					@remove="organizer.remove(group.category!)"
					@add="$emit('add', group.key)"
				/>
			</header>

			<TransitionGroup
				v-if="!collapsed.has(group.key)"
				tag="ul"
				class="space-y-2"
				enter-active-class="transition duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
				enter-from-class="-translate-y-1 opacity-0"
			>
				<li
					v-for="ticketType in group.ticketTypes"
					:key="ticketType.name"
					class="transition-opacity duration-150"
					:class="{ 'opacity-40': organizer.dragging.value === ticketType.name }"
					:draggable="canWrite"
					v-on="canWrite ? organizer.drag.handle(ticketType) : {}"
				>
					<TicketTypeRow
						:ticket-type="ticketType"
						:disabled="!canWrite"
						@click="$emit('open', ticketType.name)"
					/>
				</li>
				<li v-if="!group.ticketTypes.length" key="empty">
					<!-- The empty slot is the action: it sits where the first ticket type will go. -->
					<button
						v-if="canWrite && !organizer.dragging.value"
						type="button"
						class="flex h-16 w-full items-center gap-2 rounded-4 border border-dashed border-outline-gray-3 px-3.5 text-base text-ink-gray-6 transition-[border-color,color,transform] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] [@media(hover:hover)]:hover:border-outline-gray-4 [@media(hover:hover)]:hover:text-ink-gray-8 active:scale-[0.99] motion-reduce:transform-none"
						@click="$emit('add', group.key)"
					>
						<Icon icon="lucide-plus" class="size-4" aria-hidden="true" />
						Add ticket type
						<span class="ml-auto text-sm text-ink-gray-5">or drag one here</span>
					</button>
					<p
						v-else
						class="flex h-16 items-center justify-center rounded-4 border border-dashed border-outline-gray-3 text-sm text-ink-gray-5"
					>
						{{ organizer.dragging.value ? "Drop here to move" : "No ticket types yet" }}
					</p>
				</li>
			</TransitionGroup>
		</section>

		<p
			v-if="canWrite && organizer.groups.value.length > 1"
			class="flex items-center gap-1.5 text-sm text-ink-gray-5"
		>
			<Icon icon="lucide-move" class="size-3.5" aria-hidden="true" />
			Drag ticket types between categories to move them.
		</p>
	</div>
</template>
