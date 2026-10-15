<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"
import { computed } from "vue"

import type { TicketCategoryItem } from "@/types"

// Board columns run left to right, grouped sections top to bottom. A narrow board header
// folds the category actions into a menu.
const props = defineProps<{
	category: TicketCategoryItem | null
	first?: boolean
	last?: boolean
	horizontal?: boolean
	menu?: boolean
}>()
const emit = defineEmits<{ edit: []; remove: []; add: []; move: [step: -1 | 1] }>()

const arrows = computed(() => [
	{
		icon: props.horizontal ? "lucide-arrow-left" : "lucide-arrow-up",
		label: props.horizontal ? "Move left" : "Move up",
		disabled: props.first,
		onClick: () => emit("move", -1),
	},
	{
		icon: props.horizontal ? "lucide-arrow-right" : "lucide-arrow-down",
		label: props.horizontal ? "Move right" : "Move down",
		disabled: props.last,
		onClick: () => emit("move", 1),
	},
])

const categoryActions = [
	{ icon: "lucide-pencil", label: "Edit category", onClick: () => emit("edit") },
	{ icon: "lucide-trash-2", label: "Delete category", onClick: () => emit("remove") },
]

const menuOptions = computed(() => [
	categoryActions[0],
	...arrows.value.filter((arrow) => !arrow.disabled),
	{ ...categoryActions[1], theme: "red" as const },
])
</script>

<template>
	<div class="flex shrink-0 items-center">
		<Dropdown
			v-if="category && menu"
			:options="menuOptions"
			align="end"
			:button="{ variant: 'ghost', icon: 'lucide-ellipsis', label: 'Category actions' }"
		/>
		<template v-else-if="category">
			<!-- Reordering is occasional: the arrows wait for a pointer over the header. -->
			<div
				v-if="!(first && last)"
				class="flex transition-opacity duration-150 ease-out [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 [@media(hover:hover)]:group-focus-within:opacity-100"
			>
				<Button
					v-for="arrow in arrows"
					:key="arrow.label"
					variant="ghost"
					v-bind="arrow"
					:tooltip="arrow.label"
				/>
			</div>
			<Button
				v-for="action in categoryActions"
				:key="action.label"
				variant="ghost"
				v-bind="action"
				:tooltip="action.label"
			/>
		</template>
		<Button
			variant="ghost"
			icon="lucide-plus"
			label="Add ticket type"
			tooltip="Add ticket type"
			@click="$emit('add')"
		/>
	</div>
</template>
