<script setup lang="ts">
import { Button, Icon } from "frappe-ui"
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
			class="-m-1 space-y-1.5 rounded-xl p-1 outline-dashed outline-[1.5px] transition-colors duration-150 ease-out"
			:class="
				organizer.dropTarget.value === group.key
					? 'bg-surface-gray-1 outline-outline-gray-4'
					: 'outline-transparent'
			"
			v-on="canWrite ? organizer.drag.zone(group.key) : {}"
		>
			<header class="group flex min-h-8 items-center gap-1.5 pl-1">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-down"
					:aria-label="collapsed.has(group.key) ? 'Expand' : 'Collapse'"
					:aria-expanded="!collapsed.has(group.key)"
					class="transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
					:class="{ '-rotate-90': collapsed.has(group.key) }"
					@click="toggle(group.key)"
				/>
				<h3
					class="text-base font-semibold"
					:class="group.category ? 'text-ink-gray-9' : 'text-ink-gray-6'"
				>
					{{ group.title }}
				</h3>
				<span class="rounded-full bg-surface-gray-2 px-1.5 text-sm tabular-nums text-ink-gray-5">
					{{ group.ticketTypes.length }}
				</span>
				<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-5">{{
					group.category?.description
				}}</span>
				<TicketCategoryActions
					v-if="canWrite"
					:category="group.category"
					:first="index === 0"
					:last="!organizer.groups.value[index + 1]?.category"
					@move="organizer.shift(group.category!, $event)"
					@edit="$emit('editCategory', group.category!)"
					@remove="organizer.remove(group.category!)"
					@add="$emit('add', group.key)"
				/>
			</header>

			<ul v-if="!collapsed.has(group.key)" class="space-y-2">
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
				<li
					v-if="!group.ticketTypes.length"
					class="rounded-4 border border-dashed border-outline-gray-2 p-4 text-center text-sm text-ink-gray-5"
				>
					{{
						organizer.dragging.value
							? "Drop here to move"
							: "No ticket types yet. Drag one here or add one."
					}}
				</li>
			</ul>
		</section>

		<p
			v-if="canWrite && organizer.groups.value.length > 1"
			class="flex items-center gap-1.5 text-sm text-ink-gray-5"
		>
			<Icon name="lucide-move" class="size-3.5" aria-hidden="true" />
			Drag ticket types between categories to move them.
		</p>
	</div>
</template>
