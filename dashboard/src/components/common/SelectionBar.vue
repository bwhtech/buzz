<script setup lang="ts">
import { Button } from "frappe-ui"

/** The bar a list shows while rows are selected: what is selected, and what can be done. */
defineProps<{ count: number; label: string }>()
defineEmits<{ clear: [] }>()
</script>

<template>
	<Transition name="bar">
		<div
			v-if="count"
			role="toolbar"
			:aria-label="label"
			class="flex flex-wrap items-center gap-2 rounded-6 border border-outline-gray-2 bg-surface-gray-1 px-3 py-2"
		>
			<span class="text-sm text-ink-gray-7">{{ label }}</span>

			<div class="ml-auto flex items-center gap-2">
				<slot />

				<Button variant="ghost" :label="__('Clear selection')" @click="$emit('clear')">
					<template #icon>
						<span class="lucide-x size-4" />
					</template>
				</Button>
			</div>
		</div>
	</Transition>
</template>

<style scoped>
.bar-enter-active,
.bar-leave-active {
	transition:
		opacity 120ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}

.bar-enter-from,
.bar-leave-to {
	opacity: 0;
	transform: translateY(-4px);
}

@media (prefers-reduced-motion: reduce) {
	.bar-enter-from,
	.bar-leave-to {
		transform: none;
	}
}
</style>
