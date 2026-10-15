<script setup lang="ts">
import { Button, Tooltip } from "frappe-ui"
import { computed } from "vue"

import type { TicketCategoryItem } from "@/types"

// Board columns run left to right, grouped sections top to bottom.
const props = defineProps<{
	category: TicketCategoryItem | null
	first?: boolean
	last?: boolean
	horizontal?: boolean
}>()
defineEmits<{ edit: []; remove: []; add: []; move: [step: -1 | 1] }>()

const arrows = computed(() =>
	props.horizontal
		? { back: ["lucide-arrow-left", "Move left"], forward: ["lucide-arrow-right", "Move right"] }
		: { back: ["lucide-arrow-up", "Move up"], forward: ["lucide-arrow-down", "Move down"] },
)
</script>

<template>
	<div class="flex shrink-0 items-center">
		<template v-if="category">
			<!-- Reordering is occasional: the arrows wait for a pointer over the header. -->
			<div
				v-if="!(first && last)"
				class="flex transition-opacity duration-150 ease-out [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 [@media(hover:hover)]:group-focus-within:opacity-100"
			>
				<Tooltip :text="arrows.back[1]">
					<Button
						variant="ghost"
						:icon="arrows.back[0]"
						:aria-label="arrows.back[1]"
						:disabled="first"
						@click="$emit('move', -1)"
					/>
				</Tooltip>
				<Tooltip :text="arrows.forward[1]">
					<Button
						variant="ghost"
						:icon="arrows.forward[0]"
						:aria-label="arrows.forward[1]"
						:disabled="last"
						@click="$emit('move', 1)"
					/>
				</Tooltip>
			</div>
			<Tooltip text="Edit category">
				<Button
					variant="ghost"
					icon="lucide-pencil"
					aria-label="Edit category"
					@click="$emit('edit')"
				/>
			</Tooltip>
			<Tooltip text="Delete category">
				<Button
					variant="ghost"
					icon="lucide-trash-2"
					aria-label="Delete category"
					@click="$emit('remove')"
				/>
			</Tooltip>
		</template>
		<Tooltip text="Add ticket type">
			<Button
				variant="ghost"
				icon="lucide-plus"
				aria-label="Add ticket type"
				@click="$emit('add')"
			/>
		</Tooltip>
	</div>
</template>
