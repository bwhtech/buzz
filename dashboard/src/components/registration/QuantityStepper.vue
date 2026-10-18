<template>
	<Button
		v-if="!quantity"
		variant="outline"
		:size="size"
		icon-left="lucide-plus"
		:aria-label="__('Add {0}', [label])"
		@click="emit('change', 1)"
	>
		{{ __("Add") }}
	</Button>
	<div v-else class="flex items-center gap-1">
		<Button
			variant="outline"
			:size="size"
			icon="lucide-minus"
			:aria-label="__('Remove one {0}', [label])"
			@click="emit('change', -1)"
		/>
		<span
			class="w-6 text-center text-base font-semibold tabular-nums text-ink-gray-9"
			aria-live="polite"
		>
			{{ quantity }}
		</span>
		<Button
			variant="outline"
			:size="size"
			icon="lucide-plus"
			:disabled="quantity >= max"
			:aria-label="__('Add one {0}', [label])"
			@click="emit('change', 1)"
		/>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"

withDefaults(
	defineProps<{ quantity: number; label: string; max?: number; size?: "sm" | "md" | "lg" }>(),
	{
		max: 10,
		size: "sm",
	},
)
const emit = defineEmits<{ change: [delta: number] }>()
</script>
