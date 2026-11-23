<script setup lang="ts">
import { Button } from "frappe-ui"

// A detail left for later on the create page. The whole tile fills it in now: the button is
// the keyboard target, and its click bubbles up to the tile's handler.
const props = defineProps<{
	icon: string
	title: string
	actionLabel: string
	disabled?: boolean
}>()
const emit = defineEmits<{ action: [] }>()

const act = () => !props.disabled && emit("action")
</script>

<template>
	<div
		class="tile flex items-center gap-3 rounded-5 border border-dashed border-outline-gray-3 bg-surface-gray-1 py-3 pl-3.5 pr-3"
		:class="disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'"
		:data-disabled="disabled || undefined"
		@click="act"
	>
		<span :class="icon" class="size-[18px] shrink-0 text-ink-gray-5" aria-hidden="true" />
		<div class="min-w-0 flex-1">
			<p class="text-base font-medium text-ink-gray-8">{{ title }}</p>
			<p class="text-p-sm text-ink-gray-5">
				{{ __("You can add it any time from the event page.") }}
			</p>
		</div>
		<Button variant="outline" :label="actionLabel" :disabled="disabled" />
	</div>
</template>

<style scoped>
.tile {
	transition:
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 150ms ease,
		border-color 150ms ease;
}
.tile:not([data-disabled]):active {
	transform: scale(0.99);
}
@media (hover: hover) and (pointer: fine) {
	.tile:not([data-disabled]):hover {
		border-color: var(--outline-gray-4);
		background-color: var(--surface-gray-2);
	}
}
@media (prefers-reduced-motion: reduce) {
	.tile:not([data-disabled]):active {
		transform: none;
	}
}
</style>
