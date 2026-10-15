<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed, ref } from "vue"

import type { TicketTypeOrganizer } from "@/composables/useTicketTypeOrganizer"
import type { TicketCategoryItem } from "@/types"

import TicketTypeRow from "./TicketTypeRow.vue"

// Phones have no drag and drop: a chip filters to one category, and the drawer moves a ticket type.
const props = defineProps<{ organizer: TicketTypeOrganizer; canWrite?: boolean }>()
defineEmits<{
	open: [name: string]
	addCategory: []
	editCategory: [category: TicketCategoryItem]
}>()

const ALL = "all"
const selected = ref(ALL)

const groups = props.organizer.groups
const selectedGroup = computed(() => groups.value.find((group) => group.key === selected.value))
const visibleGroups = computed(() => (selectedGroup.value ? [selectedGroup.value] : groups.value))
const activeKey = computed(() => selectedGroup.value?.key ?? ALL)
const chips = computed(() => [
	{ key: ALL, title: "All", count: null },
	...groups.value.map((group) => ({
		key: group.key,
		title: group.title,
		count: group.ticketTypes.length,
	})),
])
</script>

<template>
	<div class="space-y-4">
		<div
			v-if="groups.length > 1 || canWrite"
			class="-mx-4 flex gap-1.5 overflow-x-auto px-4 [scrollbar-width:none]"
		>
			<Button
				v-for="chip in chips"
				:key="chip.key"
				size="md"
				class="shrink-0 rounded-full"
				:variant="activeKey === chip.key ? 'solid' : 'subtle'"
				:aria-pressed="activeKey === chip.key"
				@click="selected = chip.key"
			>
				{{ chip.title }}
				<span v-if="chip.count != null" class="tabular-nums opacity-70">{{ chip.count }}</span>
			</Button>
			<Button
				v-if="canWrite"
				size="md"
				variant="outline"
				icon-left="lucide-plus"
				label="New"
				class="shrink-0 rounded-full border-dashed"
				@click="$emit('addCategory')"
			/>
		</div>

		<section v-for="group in visibleGroups" :key="group.key" class="space-y-1.5">
			<header v-if="selectedGroup" class="flex items-start gap-2 px-0.5 pb-1">
				<div class="min-w-0 flex-1">
					<h3 class="text-base font-semibold text-ink-gray-9">{{ group.title }}</h3>
					<p v-if="group.category?.description" class="text-p-sm text-ink-gray-5">
						{{ group.category.description }}
					</p>
				</div>
				<template v-if="canWrite && group.category">
					<Button
						size="md"
						variant="ghost"
						icon="lucide-pencil"
						label="Edit category"
						@click="$emit('editCategory', group.category)"
					/>
					<Button
						size="md"
						variant="ghost"
						icon="lucide-trash-2"
						label="Delete category"
						@click="organizer.remove(group.category)"
					/>
				</template>
			</header>
			<h3
				v-else-if="groups.length > 1"
				class="flex items-baseline gap-1.5 px-0.5 text-sm font-semibold text-ink-gray-7"
			>
				{{ group.title }}
				<span class="text-xs font-normal tabular-nums text-ink-gray-5">{{
					group.ticketTypes.length
				}}</span>
			</h3>
			<ul class="space-y-2">
				<li v-for="ticketType in group.ticketTypes" :key="ticketType.name">
					<TicketTypeRow
						:ticket-type="ticketType"
						:disabled="!canWrite"
						@click="$emit('open', ticketType.name)"
					/>
				</li>
			</ul>
			<p v-if="!group.ticketTypes.length" class="py-5 text-center text-sm text-ink-gray-5">
				No ticket types in this category yet
			</p>
		</section>
	</div>
</template>
